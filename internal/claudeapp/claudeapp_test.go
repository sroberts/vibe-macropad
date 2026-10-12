package claudeapp

import "testing"

func TestLink(t *testing.T) {
	for _, tc := range []struct{ key, want string }{
		{"ATTN", "claude://code/needs-input"},
		{"A1", ""},
		{"ZOOM", ""},
		{"", ""},
	} {
		if got := Link(tc.key); got != tc.want {
			t.Errorf("Link(%q) = %q, want %q", tc.key, got, tc.want)
		}
	}
}
