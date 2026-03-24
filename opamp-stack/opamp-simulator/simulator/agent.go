package simulator

import (
	"context"
	"crypto/tls"
	"fmt"
	"log"
	"sync/atomic"
	"time"

	"github.com/google/uuid"

	"github.com/open-telemetry/opamp-go/client"
	"github.com/open-telemetry/opamp-go/client/types"
	"github.com/open-telemetry/opamp-go/protobufs"
)

// SimAgent represents a single simulated OpenTelemetry agent.
type SimAgent struct {
	index    int
	cfg      *Config
	uid      uuid.UUID
	hostname string
	healthy  bool

	opampClient     client.OpAMPClient
	effectiveConfig string
	logger          *log.Logger

	connected atomic.Bool
	stopped   atomic.Bool
}

// NewSimAgent creates a new simulated agent with the given index.
func NewSimAgent(index int, cfg *Config) *SimAgent {
	uid, err := uuid.NewV7()
	if err != nil {
		panic(err)
	}

	hostname := fmt.Sprintf("%s-%05d", cfg.Agent.HostnamePrefix, index)

	// Determine health based on unhealthy_percent
	healthy := true
	if cfg.Agent.UnhealthyPercent > 0 && (index%100) < cfg.Agent.UnhealthyPercent {
		healthy = false
	}

	// Build per-agent effective config (add a comment with agent index for uniqueness)
	effConfig := fmt.Sprintf("# Agent: %s (index=%d)\n%s", hostname, index, cfg.EffConfig)

	agent := &SimAgent{
		index:           index,
		cfg:             cfg,
		uid:             uid,
		hostname:        hostname,
		healthy:         healthy,
		effectiveConfig: effConfig,
		logger:          log.New(log.Default().Writer(), fmt.Sprintf("[agent-%05d] ", index), log.LstdFlags|log.Lmicroseconds),
	}

	return agent
}

// Start connects the simulated agent to the OpAMP server.
func (a *SimAgent) Start(ctx context.Context, connectedCounter *atomic.Int64) error {
	a.opampClient = client.NewWebSocket(&simLogger{a.logger, a.cfg.Logging.Level})

	agentDescr := a.buildAgentDescription()
	if err := a.opampClient.SetAgentDescription(agentDescr); err != nil {
		return fmt.Errorf("set agent description: %w", err)
	}

	// Set initial health BEFORE setting capabilities that include ReportsHealth.
	// The client library validates that health is set when ReportsHealth capability is declared.
	a.setHealth()

	caps := protobufs.AgentCapabilities_AgentCapabilities_ReportsStatus |
		protobufs.AgentCapabilities_AgentCapabilities_ReportsEffectiveConfig |
		protobufs.AgentCapabilities_AgentCapabilities_ReportsHealth |
		protobufs.AgentCapabilities_AgentCapabilities_ReportsRemoteConfig
	if a.cfg.Agent.AcceptRemoteConfig {
		caps |= protobufs.AgentCapabilities_AgentCapabilities_AcceptsRemoteConfig
	}
	if err := a.opampClient.SetCapabilities(&caps); err != nil {
		return fmt.Errorf("set capabilities: %w", err)
	}

	settings := types.StartSettings{
		OpAMPServerURL: a.cfg.Server.URL,
		InstanceUid:    types.InstanceUid(a.uid),
		Callbacks: types.Callbacks{
			OnConnect: func(ctx context.Context) {
				a.connected.Store(true)
				count := connectedCounter.Add(1)
				if a.cfg.Logging.LogConnections && a.cfg.Logging.Level == "debug" {
					a.logger.Printf("Connected (%s), total: %d", a.hostname, count)
				}
			},
			OnConnectFailed: func(ctx context.Context, err error) {
				a.connected.Store(false)
				if a.cfg.Logging.Level == "debug" {
					a.logger.Printf("Connection failed: %v", err)
				}
			},
			OnError: func(ctx context.Context, err *protobufs.ServerErrorResponse) {
				a.logger.Printf("Server error: %s", err.ErrorMessage)
			},
			GetEffectiveConfig: func(ctx context.Context) (*protobufs.EffectiveConfig, error) {
				return a.composeEffectiveConfig(), nil
			},
			OnMessage:              a.onMessage,
			SaveRemoteConfigStatus: func(_ context.Context, _ *protobufs.RemoteConfigStatus) {},
		},
	}

	// Only set TLS config for wss:// URLs
	if a.cfg.Server.InsecureTLS && len(a.cfg.Server.URL) > 4 && a.cfg.Server.URL[:4] == "wss:" {
		settings.TLSConfig = &tls.Config{InsecureSkipVerify: true}
	}

	if err := a.opampClient.Start(ctx, settings); err != nil {
		return fmt.Errorf("start client: %w", err)
	}

	// Start periodic health updates
	go a.periodicHealthUpdates(ctx)

	return nil
}

// Stop gracefully disconnects the agent.
func (a *SimAgent) Stop() {
	if a.stopped.CompareAndSwap(false, true) {
		if a.opampClient != nil {
			_ = a.opampClient.Stop(context.Background())
		}
	}
}

// IsConnected returns whether the agent is currently connected.
func (a *SimAgent) IsConnected() bool {
	return a.connected.Load()
}

func (a *SimAgent) buildAgentDescription() *protobufs.AgentDescription {
	return &protobufs.AgentDescription{
		IdentifyingAttributes: []*protobufs.KeyValue{
			{
				Key:   "service.name",
				Value: &protobufs.AnyValue{Value: &protobufs.AnyValue_StringValue{StringValue: a.cfg.Agent.ServiceName}},
			},
			{
				Key:   "service.version",
				Value: &protobufs.AnyValue{Value: &protobufs.AnyValue_StringValue{StringValue: a.cfg.Agent.ServiceVersion}},
			},
			{
				Key:   "service.instance.id",
				Value: &protobufs.AnyValue{Value: &protobufs.AnyValue_StringValue{StringValue: a.uid.String()}},
			},
		},
		NonIdentifyingAttributes: []*protobufs.KeyValue{
			{
				Key:   "os.type",
				Value: &protobufs.AnyValue{Value: &protobufs.AnyValue_StringValue{StringValue: a.cfg.Agent.OSType}},
			},
			{
				Key:   "host.name",
				Value: &protobufs.AnyValue{Value: &protobufs.AnyValue_StringValue{StringValue: a.hostname}},
			},
			{
				Key:   "host.arch",
				Value: &protobufs.AnyValue{Value: &protobufs.AnyValue_StringValue{StringValue: a.cfg.Agent.HostArch}},
			},
			{
				Key:   "os.description",
				Value: &protobufs.AnyValue{Value: &protobufs.AnyValue_StringValue{StringValue: a.cfg.Agent.OSDescription}},
			},
		},
	}
}

func (a *SimAgent) composeEffectiveConfig() *protobufs.EffectiveConfig {
	return &protobufs.EffectiveConfig{
		ConfigMap: &protobufs.AgentConfigMap{
			ConfigMap: map[string]*protobufs.AgentConfigFile{
				"": {Body: []byte(a.effectiveConfig)},
			},
		},
	}
}

func (a *SimAgent) setHealth() {
	startTime := uint64(time.Now().Add(-time.Hour).UnixNano())
	statusTime := uint64(time.Now().UnixNano())

	status := "StatusOk"
	lastError := ""
	if !a.healthy {
		status = "StatusError"
		lastError = "simulated unhealthy agent"
	}

	health := &protobufs.ComponentHealth{
		Healthy:            a.healthy,
		StartTimeUnixNano:  startTime,
		StatusTimeUnixNano: statusTime,
		Status:             status,
		LastError:          lastError,
		ComponentHealthMap: map[string]*protobufs.ComponentHealth{
			"extensions": {
				Healthy:            a.healthy,
				StatusTimeUnixNano: statusTime,
				Status:             status,
				ComponentHealthMap: map[string]*protobufs.ComponentHealth{
					"extension:health_check": {
						Healthy:            true,
						StatusTimeUnixNano: statusTime,
						Status:             "StatusOk",
					},
					"extension:opamp": {
						Healthy:            true,
						StatusTimeUnixNano: statusTime,
						Status:             "StatusOk",
					},
				},
			},
			"pipeline:traces": {
				Healthy:            a.healthy,
				StatusTimeUnixNano: statusTime,
				Status:             status,
				ComponentHealthMap: map[string]*protobufs.ComponentHealth{
					"receiver:otlp": {
						Healthy:            true,
						StatusTimeUnixNano: statusTime,
						Status:             "StatusOk",
					},
					"processor:memory_limiter": {
						Healthy:            true,
						StatusTimeUnixNano: statusTime,
						Status:             "StatusOk",
					},
					"processor:batch": {
						Healthy:            true,
						StatusTimeUnixNano: statusTime,
						Status:             "StatusOk",
					},
					"exporter:otlp": {
						Healthy:            a.healthy,
						StatusTimeUnixNano: statusTime,
						Status:             status,
						LastError:          lastError,
					},
				},
			},
			"pipeline:metrics": {
				Healthy:            a.healthy,
				StatusTimeUnixNano: statusTime,
				Status:             status,
				ComponentHealthMap: map[string]*protobufs.ComponentHealth{
					"receiver:otlp": {
						Healthy:            true,
						StatusTimeUnixNano: statusTime,
						Status:             "StatusOk",
					},
					"receiver:hostmetrics": {
						Healthy:            true,
						StatusTimeUnixNano: statusTime,
						Status:             "StatusOk",
					},
					"processor:memory_limiter": {
						Healthy:            true,
						StatusTimeUnixNano: statusTime,
						Status:             "StatusOk",
					},
					"processor:batch": {
						Healthy:            true,
						StatusTimeUnixNano: statusTime,
						Status:             "StatusOk",
					},
					"exporter:otlp": {
						Healthy:            a.healthy,
						StatusTimeUnixNano: statusTime,
						Status:             status,
						LastError:          lastError,
					},
				},
			},
			"pipeline:logs": {
				Healthy:            a.healthy,
				StatusTimeUnixNano: statusTime,
				Status:             status,
				ComponentHealthMap: map[string]*protobufs.ComponentHealth{
					"receiver:otlp": {
						Healthy:            true,
						StatusTimeUnixNano: statusTime,
						Status:             "StatusOk",
					},
					"processor:memory_limiter": {
						Healthy:            true,
						StatusTimeUnixNano: statusTime,
						Status:             "StatusOk",
					},
					"processor:batch": {
						Healthy:            true,
						StatusTimeUnixNano: statusTime,
						Status:             "StatusOk",
					},
					"exporter:otlp": {
						Healthy:            a.healthy,
						StatusTimeUnixNano: statusTime,
						Status:             status,
						LastError:          lastError,
					},
				},
			},
		},
	}

	_ = a.opampClient.SetHealth(health)
}

func (a *SimAgent) periodicHealthUpdates(ctx context.Context) {
	ticker := time.NewTicker(time.Duration(a.cfg.Agent.HealthIntervalSeconds) * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			if a.stopped.Load() {
				return
			}
			a.setHealth()
		}
	}
}

func (a *SimAgent) onMessage(ctx context.Context, msg *types.MessageData) {
	if msg.RemoteConfig != nil {
		// Apply remote config — in the simulator we just accept it
		if a.cfg.Agent.AcceptRemoteConfig {
			// Merge: use the instance config as our effective config
			if instanceCfg, ok := msg.RemoteConfig.Config.ConfigMap[""]; ok && len(instanceCfg.Body) > 0 {
				a.effectiveConfig = string(instanceCfg.Body)
			}

			a.opampClient.SetRemoteConfigStatus(&protobufs.RemoteConfigStatus{
				LastRemoteConfigHash: msg.RemoteConfig.ConfigHash,
				Status:               protobufs.RemoteConfigStatuses_RemoteConfigStatuses_APPLIED,
			})

			_ = a.opampClient.UpdateEffectiveConfig(ctx)
		}
	}
}

// simLogger adapts *log.Logger to the types.Logger interface.
type simLogger struct {
	l     *log.Logger
	level string
}

func (s *simLogger) Debugf(ctx context.Context, format string, args ...interface{}) {
	if s.level == "debug" {
		s.l.Printf("[DEBUG] "+format, args...)
	}
}

func (s *simLogger) Errorf(ctx context.Context, format string, args ...interface{}) {
	s.l.Printf("[ERROR] "+format, args...)
}
