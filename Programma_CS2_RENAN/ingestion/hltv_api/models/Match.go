package models

type Match struct {
	MatchID  string
	Event    string
	Stage    string
	TeamA    string
	TeamB    string
	BO       string
	IsLive   bool
	MatchURL string
}
