// Package claudeapp opens the Claude desktop app's Code session that is
// waiting for you, for the pad's ATTN key.
//
// The app has no shortcut for it, but it registers a claude:// link,
// code/needs-input, that opens the waiting session (Claude.app 2.31226:
// claudeURLHandler). The link isn't documented, so it may change. The other
// session keys need no help from Tally: Cmd+1..9 open the sidebar's items.
package claudeapp

import (
	"fmt"
	"os/exec"
)

// Link is the claude:// link a pad key opens, or "" when the key has none.
func Link(key string) string {
	if key == "ATTN" {
		return "claude://code/needs-input"
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
