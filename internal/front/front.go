// Package front reports which app is frontmost on macOS, so the pad can
// send the Claude app's shortcuts instead of herdr's while it is in front.
//
// It asks lsappinfo, which needs no Accessibility or Screen Recording
// permission. That tells apps apart but not windows or tabs: Chat and Code
// in the Claude app look the same.
package front

import (
	"os/exec"
	"regexp"
	"strings"
)

// Claude is the frame's app value while the Claude app is in front.
const Claude = "claude"

// Apps maps bundle identifiers to the frame's app values.
var Apps = map[string]string{
	"com.anthropic.claudefordesktop": Claude,
}

var bundleID = regexp.MustCompile(`"?bundleID"?="([^"]*)"`)

// ParseBundleID pulls the bundle identifier out of
// `lsappinfo info -only bundleid` output, or "" when there is none.
func ParseBundleID(out string) string {
	if m := bundleID.FindStringSubmatch(out); m != nil {
		return m[1]
	}
	return ""
}

// App is the frame's app value for a bundle identifier: "" for any app the
// pad has no shortcuts for.
func App(bundle string) string {
	return Apps[bundle]
}

// Frontmost returns the frontmost app's frame value, or "" when it has none
// or lsappinfo fails.
func Frontmost() string {
	asn, err := exec.Command("lsappinfo", "front").Output()
	if err != nil {
		return ""
	}
	out, err := exec.Command("lsappinfo", "info", "-only", "bundleid", strings.TrimSpace(string(asn))).Output()
	if err != nil {
		return ""
	}
	return App(ParseBundleID(string(out)))
}
