package livenow

import (
	"fmt"
	"hltv/models"
	webclient "hltv/webClient"
	"time"

	"github.com/go-rod/rod"
	"github.com/go-rod/stealth"
)

func ExtractLiveNow(date string) (list []models.Match, err error) {
	web := webclient.StartWebclient()
	defer web.MustClose()
	page := stealth.MustPage(web)
	page.MustNavigate(fmt.Sprintf("https://www.hltv.org/matches?selectedDate=%v", date))
	var emptyText string

	_ = rod.Try(func() {
		emptyText = page.
			MustElement("#for-you-empty-div").
			MustElement("b").
			MustText()
	})

	if emptyText != "" {
		return nil, fmt.Errorf("No matches running now")
	}
	el := page.MustElement("body > div.bgPadding > div.widthControl > div:nth-child(2) > div.contentCol > div.matches-v4 > div.new-standardPageGrid > div.mainContent > div.matches-list-column > div.matches-chronologically > div > div")
	html := string(el.MustHTML())
	err = rod.Try(func() {
		page.Timeout(5 * time.Second).MustElement("body")
	})
	if err != nil {
		return nil, fmt.Errorf("Body not load")
	}
	data, err := ExtractInfFromHTML(html)
	if err != nil {
		return nil, nil
	}
	return data, nil

}
