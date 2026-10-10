// Package claudeapp finds the Claude desktop app's Code sessions and opens
// them, so the pad's A1..A6 keys can jump between them as they do between
// herdr agents.
//
// The app keeps one JSON file per session under its Application Support
// folder, and registers claude:// links: code/continue?session=<id> opens a
// session and code/needs-input opens the one waiting for you (Claude.app
// 2.31226: claudeURLHandler). Neither is documented, so both may change.
//
// The decoder keeps only ids, the archived flag and two timestamps: session
// titles and folders never leave the file.
package claudeapp

import (
	"encoding/json"
	"fmt"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
)

// Session is one Code session in the app.
type Session struct {
	ID           string `json:"sessionId"`
	Archived     bool   `json:"isArchived"`
	LastActivity int64  `json:"lastActivityAt"` // ms since the epoch
	LastFocused  int64  `json:"lastFocusedAt"`
}

// validID is the app's own check for a local session id in a link.
var validID = regexp.MustCompile(`^local_[A-Za-z0-9-]{1,64}$`)

// Dir is where the app keeps its Code sessions.
func Dir(home string) string {
	return filepath.Join(home, "Library", "Application Support", "Claude", "claude-code-sessions")
}

// Load returns the sessions the app lists, most recent activity first, as
// its own "recent sessions" menus order them. Archived sessions and files it
// can't read are left out.
func Load(dir string) ([]Session, error) {
	paths, err := filepath.Glob(filepath.Join(dir, "*", "*", "local_*.json"))
	if err != nil {
		return nil, err
	}
	var out []Session
	for _, p := range paths {
		b, err := os.ReadFile(p)
		if err != nil {
			continue
		}
		var s Session
		if json.Unmarshal(b, &s) != nil || s.Archived || !validID.MatchString(s.ID) {
			continue
		}
		out = append(out, s)
	}
	Sort(out)
	return out, nil
}

// Sort orders sessions by most recent activity, then id.
func Sort(s []Session) {
	sort.Slice(s, func(i, j int) bool {
		if s[i].LastActivity != s[j].LastActivity {
			return s[i].LastActivity > s[j].LastActivity
		}
		return s[i].ID < s[j].ID
	})
}

// Focused is the 1-based position of the session focused most recently,
// which is the one the app is showing, or 0 when there are none.
func Focused(s []Session) int {
	best := 0
	for i, x := range s {
		if x.LastFocused > 0 && (best == 0 || x.LastFocused > s[best-1].LastFocused) {
			best = i + 1
		}
	}
	return best
}

// Keys are the pad keys that open sessions: slot n opens sessions[n-1].
var Keys = []string{"A1", "A2", "A3", "A4", "A5", "A6"}

// Link is the claude:// link a pad key opens, or "" when the key has none
// (no such session, or a key the app has no link for).
func Link(key string, sessions []Session) string {
	if key == "ATTN" {
		return "claude://code/needs-input"
	}
	for i, k := range Keys {
		if k == key && i < len(sessions) && validID.MatchString(sessions[i].ID) {
			return "claude://code/continue?session=" + url.QueryEscape(sessions[i].ID)
		}
	}
	return ""
}

// Open hands a claude:// link to the app.
func Open(link string) error {
	if out, err := exec.Command("open", link).CombinedOutput(); err != nil {
		return fmt.Errorf("open %s: %v: %s", link, err, out)
	}
	return nil
}
