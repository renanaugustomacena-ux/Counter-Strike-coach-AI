package heatmapmatch

import (
	"fmt"
	webclient "hltv/webClient"
)

func GetHeatMap(MatchId string, MatchDescription string) (img []byte) {
	web := webclient.StartWebclient()
	defer web.MustClose()
	page := web.MustPage(fmt.Sprintf("https://www.hltv.org/stats/matches/heatmap/mapstatsid/%v/%v", MatchId, MatchDescription)).MustWindowFullscreen()
	el := page.MustElement("body > div.bgPadding > div.widthControl > div:nth-child(2) > div.contentCol > div.stats-section.stats-match.stats-match-heatmap > div.heatmap-holder")
	data := el.MustScreenshot()
	return data
}
