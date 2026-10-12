package front

import "testing"

// Captured from lsappinfo on macOS 27 with the Claude app in front.
const claudeInFront = `[ NULL ]  ASN:0x0-0x6e56e5: (in front) 
    bundleID="com.anthropic.claudefordesktop"
    bundle path=[ NULL ] 
    executable path=[ NULL ] 
 !cgsConnection !signalled type=[ NULL ]  flavor=[ NULL ]  Version=[ NULL ]  Arch=!!none
`

func TestParseBundleID(t *testing.T) {
	for _, tc := range []struct{ out, want string }{
		{claudeInFront, "com.anthropic.claudefordesktop"},
		{`"bundleID"="com.google.Chrome"`, "com.google.Chrome"},
		{"", ""},
		{"[ NULL ]  ASN:0x0-0x1: \n", ""},
	} {
		if got := ParseBundleID(tc.out); got != tc.want {
			t.Errorf("ParseBundleID(%q) = %q, want %q", tc.out, got, tc.want)
		}
	}
}

func TestApp(t *testing.T) {
	if got := App("com.anthropic.claudefordesktop"); got != Claude {
		t.Errorf("Claude app = %q", got)
	}
	for _, b := range []string{"com.google.Chrome", "com.mitchellh.ghostty", ""} {
		if got := App(b); got != "" {
			t.Errorf("App(%q) = %q, want none", b, got)
		}
	}
}
