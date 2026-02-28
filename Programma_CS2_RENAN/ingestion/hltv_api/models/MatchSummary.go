package models

type MapVeto struct {
	TeamName   string
	MapName    string
	TeamChoice string
}

type TeamResult struct {
	TeamName string
	WonMaps  int
}
type MapResult struct {
	MapName string
	Team1   TeamResult
	Team2   TeamResult
	Url     string
}

type Player struct {
	PlayerName string
	KD         string
	Swing      float64
	ADR        float64
	KAST       float64
	Rating30   float64
}

type TeamStats struct {
	TeamName     string
	PlayersStats []Player
}
