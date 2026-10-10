package device

import "testing"

func TestLinkPassesKeyMessagesOn(t *testing.T) {
	l, pads := testLink(t, nil)
	keys := make(chan string, 10)
	l.OnKey = func(k string) { keys <- k }
	l.Send([]byte("F1\n"))
	run(t, l)
	p := next(t, pads, "a connection")
	expectLine(t, p, "F1\n")

	for _, line := range []string{
		`{"t":"key","k":"A3"}`,
		`{"t":"key"}`,        // no key: ignored
		`{"t":"key","k":""}`, // empty: ignored
		`not json`,
		`{"t":"key","k":"ATTN"}`,
	} {
		if _, err := p.conn.Write([]byte(line + "\n")); err != nil {
			t.Fatal(err)
		}
	}
	if k := next(t, keys, "A3"); k != "A3" {
		t.Errorf("key = %q, want A3", k)
	}
	if k := next(t, keys, "ATTN"); k != "ATTN" {
		t.Errorf("key = %q, want ATTN", k)
	}
}

func TestKeyMessageWithoutOnKey(t *testing.T) {
	l, pads := testLink(t, nil)
	l.Send([]byte("F1\n"))
	run(t, l)
	p := next(t, pads, "a connection")
	expectLine(t, p, "F1\n")
	if _, err := p.conn.Write([]byte(`{"t":"key","k":"A1"}` + "\n" + `{"t":"hello","v":2}` + "\n")); err != nil {
		t.Fatal(err)
	}
	expectLine(t, p, "F1\n") // still serving: the hello brings a resend
}
