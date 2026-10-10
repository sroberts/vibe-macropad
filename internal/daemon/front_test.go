package daemon

import (
	"errors"
	"strings"
	"sync"
	"testing"
	"time"
)

// frontApp is a Config.Front whose answer a test can change.
type frontApp struct {
	mu  sync.Mutex
	app string
}

func (f *frontApp) get() string {
	f.mu.Lock()
	defer f.mu.Unlock()
	return f.app
}

func (f *frontApp) set(app string) {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.app = app
}

func TestFrontmostAppSetsTheFrame(t *testing.T) {
	app := &frontApp{}
	cfg := testConfig()
	cfg.Front, cfg.FrontPoll = app.get, 10*time.Millisecond
	frames := start(t, cfg, newFake(agent("w1:p1", "working")))
	if got := next(t, frames, "the first frame"); got.App != "" {
		t.Fatalf("first frame app = %q", got.App)
	}

	app.set("claude")
	got := next(t, frames, "a frame for the Claude app")
	if got.App != "claude" || *got.Slots[0] != "W" {
		t.Errorf("frame = %s", got.JSON())
	}
	if want := `"app":"claude"`; !strings.Contains(string(got.JSON()), want) {
		t.Errorf("frame = %s, want %s", got.JSON(), want)
	}

	app.set("")
	if got := next(t, frames, "a frame back in the terminal"); got.App != "" {
		t.Errorf("frame = %s", got.JSON())
	}
	nothing(t, frames, "frame while the front app stays the same")
}

func TestFrontmostAppWhileHerdrIsOffline(t *testing.T) {
	app := &frontApp{app: "claude"}
	cfg := testConfig()
	cfg.Front, cfg.FrontPoll = app.get, 10*time.Millisecond
	f := newFake()
	f.err = errors.New("herdr is not reachable")
	frames := start(t, cfg, f)
	for {
		got := next(t, frames, "an offline frame for the Claude app")
		if got.Herdr {
			t.Fatalf("frame = %s", got.JSON())
		}
		if got.App == "claude" {
			return
		}
	}
}

func TestClaudeAppSessionsInTheFrame(t *testing.T) {
	front := &frontApp{app: "claude"}
	var mu sync.Mutex
	count, focus, reads := 3, 2, 0
	cfg := testConfig()
	cfg.Front, cfg.FrontPoll, cfg.SessionPoll = front.get, 10*time.Millisecond, 30*time.Millisecond
	cfg.AppSessions = func() (int, int) {
		mu.Lock()
		defer mu.Unlock()
		reads++
		return count, focus
	}
	frames := start(t, cfg, newFake(agent("w1:p1", "idle")))
	for {
		got := next(t, frames, "a frame with the app's sessions")
		if got.App == "claude" {
			if got.ASess != 3 || got.AFocus != 2 {
				t.Fatalf("frame = %s", got.JSON())
			}
			if want := `"app":"claude","asess":3,"afocus":2`; !strings.Contains(string(got.JSON()), want) {
				t.Errorf("frame = %s, want %s", got.JSON(), want)
			}
			break
		}
	}

	mu.Lock()
	focus = 1
	mu.Unlock()
	if got := next(t, frames, "a frame after the app's focus moved"); got.AFocus != 1 {
		t.Errorf("frame = %s", got.JSON())
	}

	front.set("")
	got := next(t, frames, "a frame back in the terminal")
	if got.App != "" || got.ASess != 0 || got.AFocus != 0 {
		t.Errorf("frame = %s", got.JSON())
	}
	mu.Lock()
	before := reads
	mu.Unlock()
	time.Sleep(100 * time.Millisecond)
	mu.Lock()
	defer mu.Unlock()
	if reads != before {
		t.Errorf("read the app's sessions %d times with the app in back", reads-before)
	}
}
