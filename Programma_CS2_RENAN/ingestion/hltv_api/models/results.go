package models

type Team struct {
	Name    string
	WonMaps int
}
type Results struct {
	MatchUrl string
	Team1    Team
	Team2    Team
	Event    string
	BO       string
	Date     string
}
