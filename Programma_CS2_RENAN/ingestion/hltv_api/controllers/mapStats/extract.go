package mapstats

import (
	"fmt"
	webclient "hltv/webClient"
	"time"

	"github.com/go-rod/rod"
	"github.com/go-rod/stealth"
)

func ExtractMatches(MatchId string, MatchDescription string) (data map[string]interface{}, err error) {
	web := webclient.StartWebclient()
	defer web.MustClose()
	page := stealth.MustPage(web)
	url := fmt.Sprintf("https://www.hltv.org/stats/matches/mapstatsid/%v/%v", MatchId, MatchDescription)
	page.MustNavigate(url)
	err = rod.Try(func() {
		page.Timeout(5 * time.Second).MustElement("body")
	})
	if err != nil {
		return nil, fmt.Errorf("Body not load")
	}
	html := page.MustElement("body > div.bgPadding > div.widthControl > div:nth-child(2) > div.contentCol > div.stats-section.stats-match > div:nth-child(13) > table").MustHTML()
	stats, err := ExtractInfFromHTML(html)
	if err != nil {
		return nil, nil
	}
	htmlTeam2 := page.MustElement("body > div.bgPadding > div.widthControl > div:nth-child(2) > div.contentCol > div.stats-section.stats-match > div:nth-child(32) > table").MustHTML()
	statsTeam2, err := ExtractInfFromHTML(htmlTeam2)
	if err != nil {
		return nil, nil
	}
	return map[string]interface{}{
		"StatsTeam1": stats,
		"StatsTeam2": statsTeam2,
	}, nil
}
