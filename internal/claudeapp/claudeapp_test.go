package claudeapp

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func write(t *testing.T, dir, name, body string) {
	t.Helper()
	p := filepath.Join(dir, "acct", "org", name)
	if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(p, []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestLoadOrdersByActivityAndDropsPrivateFields(t *testing.T) {
	dir := t.TempDir()
	write(t, dir, "local_a.json", `{"sessionId":"local_a","title":"SECRET-title","cwd":"/SECRET/cwd","lastActivityAt":100,"lastFocusedAt":5}`)
	write(t, dir, "local_b.json", `{"sessionId":"local_b","title":"SECRET-title","lastActivityAt":300,"lastFocusedAt":9}`)
	write(t, dir, "local_c.json", `{"sessionId":"local_c","isArchived":true,"lastActivityAt":900}`)
	write(t, dir, "local_d.json", `{"sessionId":"local_d","lastActivityAt":200}`)
	write(t, dir, "local_bad.json", `not json`)
	write(t, dir, "local_e.json", `{"sessionId":"../../etc","lastActivityAt":999}`)
	write(t, dir, "scheduled-tasks.json", `{"sessionId":"local_z","lastActivityAt":999}`)

	got, err := Load(dir)
	if err != nil {
		t.Fatal(err)
	}
	var ids []string
	for _, s := range got {
		ids = append(ids, s.ID)
		if strings.Contains(s.ID, "SECRET") {
			t.Errorf("private field reached a session: %+v", s)
		}
	}
	if strings.Join(ids, " ") != "local_b local_d local_a" {
		t.Errorf("sessions = %v", ids)
	}
	if f := Focused(got); f != 1 {
		t.Errorf("focused = %d, want 1 (local_b)", f)
	}
}

func TestLoadWithoutTheApp(t *testing.T) {
	got, err := Load(filepath.Join(t.TempDir(), "missing"))
	if err != nil || len(got) != 0 {
		t.Errorf("Load = %v, %v", got, err)
	}
}

func TestFocusedWithoutFocusTimes(t *testing.T) {
	if f := Focused([]Session{{ID: "local_a"}, {ID: "local_b"}}); f != 0 {
		t.Errorf("focused = %d", f)
	}
	if f := Focused(nil); f != 0 {
		t.Errorf("focused = %d", f)
	}
}

func TestLink(t *testing.T) {
	s := []Session{{ID: "local_1a-2b"}, {ID: "local_x"}}
	for _, tc := range []struct{ key, want string }{
		{"A1", "claude://code/continue?session=local_1a-2b"},
		{"A2", "claude://code/continue?session=local_x"},
		{"A3", ""}, // no third session
		{"ATTN", "claude://code/needs-input"},
		{"ZOOM", ""},
		{"", ""},
	} {
		if got := Link(tc.key, s); got != tc.want {
			t.Errorf("Link(%q) = %q, want %q", tc.key, got, tc.want)
		}
	}
	if got := Link("A1", []Session{{ID: "local_a&x=1"}}); got != "" {
		t.Errorf("an invalid id made a link: %q", got)
	}
}
