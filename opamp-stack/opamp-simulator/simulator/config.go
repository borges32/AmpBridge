package simulator

import (
	"fmt"
	"os"

	"gopkg.in/yaml.v3"
)

// Config holds the full simulator configuration loaded from YAML.
type Config struct {
	Server     ServerConfig     `yaml:"server"`
	Simulation SimulationConfig `yaml:"simulation"`
	Agent      AgentConfig      `yaml:"agent"`
	EffConfig  string           `yaml:"effective_config"`
	Logging    LoggingConfig    `yaml:"logging"`
}

type ServerConfig struct {
	URL         string `yaml:"url"`
	InsecureTLS bool   `yaml:"insecure_tls"`
}

type SimulationConfig struct {
	AgentCount      int `yaml:"agent_count"`
	SpawnRate       int `yaml:"spawn_rate"`
	DurationSeconds int `yaml:"duration_seconds"`
}

type AgentConfig struct {
	ServiceName               string `yaml:"service_name"`
	ServiceVersion            string `yaml:"service_version"`
	OSType                    string `yaml:"os_type"`
	HostnamePrefix            string `yaml:"hostname_prefix"`
	HostArch                  string `yaml:"host_arch"`
	OSDescription             string `yaml:"os_description"`
	HealthIntervalSeconds     int    `yaml:"health_interval_seconds"`
	ConfigReportIntervalSecs  int    `yaml:"config_report_interval_seconds"`
	UnhealthyPercent          int    `yaml:"unhealthy_percent"`
	AcceptRemoteConfig        bool   `yaml:"accept_remote_config"`
}

type LoggingConfig struct {
	Level            string `yaml:"level"`
	LogConnections   bool   `yaml:"log_connections"`
	ProgressInterval int    `yaml:"progress_interval"`
}

// LoadConfig reads and parses the YAML configuration file.
func LoadConfig(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("cannot read config file %s: %w", path, err)
	}

	cfg := &Config{
		// Defaults
		Server: ServerConfig{
			URL:         "ws://127.0.0.1:4320/v1/opamp",
			InsecureTLS: true,
		},
		Simulation: SimulationConfig{
			AgentCount: 100,
			SpawnRate:  50,
		},
		Agent: AgentConfig{
			ServiceName:              "io.opentelemetry.collector",
			ServiceVersion:           "0.102.1",
			OSType:                   "linux",
			HostnamePrefix:           "otel-sim",
			HostArch:                 "amd64",
			OSDescription:            "Ubuntu 22.04.4 LTS",
			HealthIntervalSeconds:    60,
			ConfigReportIntervalSecs: 120,
			UnhealthyPercent:         5,
			AcceptRemoteConfig:       true,
		},
		Logging: LoggingConfig{
			Level:            "info",
			LogConnections:   true,
			ProgressInterval: 100,
		},
	}

	if err := yaml.Unmarshal(data, cfg); err != nil {
		return nil, fmt.Errorf("cannot parse config file: %w", err)
	}

	// Validation
	if cfg.Simulation.AgentCount <= 0 {
		return nil, fmt.Errorf("simulation.agent_count must be > 0")
	}
	if cfg.Simulation.SpawnRate <= 0 {
		cfg.Simulation.SpawnRate = 50
	}
	if cfg.Agent.HealthIntervalSeconds <= 0 {
		cfg.Agent.HealthIntervalSeconds = 60
	}
	if cfg.Agent.ConfigReportIntervalSecs <= 0 {
		cfg.Agent.ConfigReportIntervalSecs = 120
	}
	if cfg.Logging.ProgressInterval <= 0 {
		cfg.Logging.ProgressInterval = 100
	}

	return cfg, nil
}
