package match

import (
	"fmt"
	"hltv/models"
	webclient "hltv/webClient"
	"time"

	"github.com/go-rod/rod"
	"github.com/go-rod/stealth"
)

func ExtractData(id string, MatchDescription string) (data map[string]interface{}, err error) {
	web := webclient.StartWebclient()
	defer web.MustClose()
	page := stealth.MustPage(web)
	url := fmt.Sprintf(fmt.Sprintf("https://www.hltv.org/matches/%v/%v", id, MatchDescription))
	page.MustNavigate(url)
	err = rod.Try(func() {
		page.Timeout(5 * time.Second).MustElement("body")
	})
	if err != nil {
		return nil, fmt.Errorf("Body not load")
	}
	html := page.MustElement("body > div.bgPadding > div.widthControl > div:nth-child(2) > div.contentCol > div.match-page > div.g-grid.maps > div.col-6.col-7-small > div:nth-child(3) > div").MustHTML()
	mapsResponse, err1 := ExtractMapsVet(html)
	if err1 != nil {
		return nil, err1
	}
	htmlResult := page.MustElement("body > div.bgPadding > div.widthControl > div:nth-child(2) > div.contentCol > div.match-page > div.g-grid.maps > div.col-6.col-7-small > div.flexbox-column").MustHTML()
	dataResult, err2 := ExtractMapsResultData(htmlResult)
	if err != nil {
		return nil, err2
	}
	htmlStats := page.MustElement("#match-stats").MustHTML()
	stats, err := ExtractPlayersStats(htmlStats)
	if err != nil {
		return nil, err
	}
	var summary map[string]interface{}
	summary = map[string]interface{}{
		"mapVetoes": mapsResponse,
		"results":   dataResult,
		"teamStats": stats,
	}
	return summary, nil
}

func ExtractMapsResult(html string) (list []models.MapResult, err error) {
	data, err := ExtractMapsResultData(html)
	if err != nil {
		return nil, nil
	}
	return data, nil
}

func ExtractPlayersStats(html string) (list []models.TeamStats, err error) {
	data, err := ExtractMapsStats(html)
	if err != nil {
		return nil, nil
	}
	return data, nil
}
