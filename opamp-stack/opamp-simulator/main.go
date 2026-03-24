package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"sync"
	"sync/atomic"
	"syscall"
	"time"

	"github.com/ampbridge/opamp-simulator/simulator"
)

func main() {
	configPath := flag.String("config", "config.yaml", "Path to configuration file")
	agentCount := flag.Int("agents", 0, "Override agent count from config")
	spawnRate := flag.Int("rate", 0, "Override spawn rate from config")
	flag.Parse()

	// Load configuration
	cfg, err := simulator.LoadConfig(*configPath)
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	// CLI overrides
	if *agentCount > 0 {
		cfg.Simulation.AgentCount = *agentCount
	}
	if *spawnRate > 0 {
		cfg.Simulation.SpawnRate = *spawnRate
	}

	log.Printf("=== OpAMP Agent Load Simulator ===")
	log.Printf("Server:      %s", cfg.Server.URL)
	log.Printf("Agents:      %d", cfg.Simulation.AgentCount)
	log.Printf("Spawn rate:  %d agents/sec", cfg.Simulation.SpawnRate)
	if cfg.Simulation.DurationSeconds > 0 {
		log.Printf("Duration:    %ds", cfg.Simulation.DurationSeconds)
	} else {
		log.Printf("Duration:    infinite (Ctrl+C to stop)")
	}
	log.Printf("Hostname:    %s-XXXXX", cfg.Agent.HostnamePrefix)
	log.Printf("Unhealthy:   %d%%", cfg.Agent.UnhealthyPercent)
	log.Printf("==================================")

	// Context for graceful shutdown
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Handle SIGINT/SIGTERM
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	// Spawn agents
	agents := make([]*simulator.SimAgent, 0, cfg.Simulation.AgentCount)
	var connectedCounter atomic.Int64
	var mu sync.Mutex

	spawnStart := time.Now()
	spawnInterval := time.Second / time.Duration(cfg.Simulation.SpawnRate)

	log.Printf("Spawning %d agents at %d/sec...", cfg.Simulation.AgentCount, cfg.Simulation.SpawnRate)

	spawned := 0
	spawnErrors := 0
	aborted := false

	for i := 0; i < cfg.Simulation.AgentCount; i++ {
		select {
		case sig := <-sigCh:
			log.Printf("Received %s during spawn, stopping...", sig)
			cancel()
			aborted = true
		default:
		}
		if aborted {
			break
		}

		agent := simulator.NewSimAgent(i, cfg)

		if err := agent.Start(ctx, &connectedCounter); err != nil {
			spawnErrors++
			log.Printf("Failed to start agent %d: %v", i, err)
			continue
		}

		mu.Lock()
		agents = append(agents, agent)
		mu.Unlock()
		spawned++

		// Progress logging
		if cfg.Logging.ProgressInterval > 0 && spawned%cfg.Logging.ProgressInterval == 0 {
			connected := connectedCounter.Load()
			elapsed := time.Since(spawnStart).Seconds()
			log.Printf("Progress: %d/%d spawned, %d connected, %.1fs elapsed, %d errors",
				spawned, cfg.Simulation.AgentCount, connected, elapsed, spawnErrors)
		}

		// Rate limiting
		if i < cfg.Simulation.AgentCount-1 {
			time.Sleep(spawnInterval)
		}
	}

	spawnDuration := time.Since(spawnStart)
	log.Printf("Spawn complete: %d agents in %.1fs (%d errors)",
		spawned, spawnDuration.Seconds(), spawnErrors)

	if !aborted {
		// Wait for connections to settle
		time.Sleep(3 * time.Second)
		connected := connectedCounter.Load()
		log.Printf("Status: %d/%d agents connected", connected, spawned)

		// Start stats reporter
		go statsReporter(ctx, &connectedCounter, spawned)

		// Wait for duration or signal
		if cfg.Simulation.DurationSeconds > 0 {
			timer := time.NewTimer(time.Duration(cfg.Simulation.DurationSeconds) * time.Second)
			select {
			case <-timer.C:
				log.Printf("Duration expired (%ds), shutting down...", cfg.Simulation.DurationSeconds)
			case sig := <-sigCh:
				log.Printf("Received %s, shutting down...", sig)
				timer.Stop()
			}
		} else {
			sig := <-sigCh
			log.Printf("Received %s, shutting down...", sig)
		}
		cancel()
	}

	// Graceful shutdown
	log.Printf("Stopping %d agents...", len(agents))
	shutdownStart := time.Now()

	var wg sync.WaitGroup
	// Stop agents in parallel batches
	batchSize := 100
	for i := 0; i < len(agents); i += batchSize {
		end := i + batchSize
		if end > len(agents) {
			end = len(agents)
		}
		batch := agents[i:end]

		wg.Add(1)
		go func(batch []*simulator.SimAgent) {
			defer wg.Done()
			for _, a := range batch {
				a.Stop()
			}
		}(batch)
	}
	wg.Wait()

	shutdownDuration := time.Since(shutdownStart)
	log.Printf("All agents stopped in %.1fs", shutdownDuration.Seconds())
	log.Printf("=== Simulation ended ===")
}

func statsReporter(ctx context.Context, counter *atomic.Int64, total int) {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			connected := counter.Load()
			disconnected := int64(total) - connected
			fmt.Printf("[STATS] Connected: %d | Disconnected: %d | Total: %d\n",
				connected, disconnected, total)
		}
	}
}
