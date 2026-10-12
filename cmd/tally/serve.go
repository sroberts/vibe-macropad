package main

import (
	"context"
	"flag"
	"fmt"
	"io"
	"log/slog"
	"os"
	"os/signal"
	"syscall"

	"github.com/sroberts/vibe-macropad/internal/claudeapp"
	"github.com/sroberts/vibe-macropad/internal/daemon"
	"github.com/sroberts/vibe-macropad/internal/device"
	"github.com/sroberts/vibe-macropad/internal/front"
	"github.com/sroberts/vibe-macropad/internal/herdr"
	"github.com/sroberts/vibe-macropad/internal/slots"
)

func serve(args []string) error {
	fs := flag.NewFlagSet("serve", flag.ExitOnError)
	portPath := fs.String("port", "", "serial port to use instead of discovery (skips the handshake)")
	cfg := daemon.Defaults()
	fs.IntVar(&cfg.Slots, "slots", cfg.Slots, "number of Fleet slot keys")
	verbose := fs.Bool("verbose", false, "also log every frame sent to the pad")
	noApps := fs.Bool("no-apps", false, "don't watch the frontmost app (the pad always sends herdr's keys)")
	fs.Usage = func() { fmt.Fprint(os.Stderr, usage) }
	fs.Parse(args)
	if !*noApps {
		cfg.Front = front.Frontmost
	}

	path, err := herdr.SocketPath()
	if err != nil {
		return err
	}
	level := slog.LevelInfo
	if *verbose {
		level = slog.LevelDebug
	}
	log := slog.New(slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{Level: level}))
	log.Info("tally serve", "herdr", path, "slots", cfg.Slots)

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	link := device.NewLink(func() (io.ReadWriteCloser, string, error) {
		if *portPath != "" {
			port, err := device.Open(*portPath)
			return port, *portPath, err
		}
		name, port, hello, err := device.Find()
		return port, fmt.Sprintf("%s (firmware %s, protocol v%d)", name, hello.FW, hello.V), err
	}, log)
	if !*noApps {
		// The pad sends ATTN here while the Claude app is in front.
		link.OnKey = func(key string) {
			go func() {
				u := claudeapp.Link(key)
				if u == "" {
					log.Debug("key opens nothing", "key", key)
					return
				}
				if err := claudeapp.Open(u); err != nil {
					log.Error("Claude app link failed", "key", key, "err", err)
				}
			}()
		}
	}
	d := daemon.New(cfg, herdr.New(path), func(f slots.Frame) {
		line, err := device.EncodeFrame(f.JSON())
		if err != nil {
			log.Error("frame not sent", "err", err)
			return
		}
		link.Send(line)
	}, log)

	done := make(chan struct{})
	go func() { link.Run(ctx); close(done) }()
	d.Run(ctx)
	<-done
	log.Info("tally serve stopped")
	return nil
}
