package results

import (
	"fmt"
	"hltv/models"
	webclient "hltv/webClient"
	"time"

	"github.com/go-rod/rod"
	"github.com/go-rod/stealth"
)

func ExtractResults() (list []models.Results, err error) {
	web := webclient.StartWebclient()
	defer web.MustClose()
	page := stealth.MustPage(web)
	url := fmt.Sprintf("https://www.hltv.org/results")
	page.MustNavigate(url)
	err = rod.Try(func() {
		page.Timeout(5 * time.Second).MustElement("body")
	})
	if err != nil {
		return nil, fmt.Errorf("Body not load")
	}

	html := page.MustElement("body > div.bgPadding > div.widthControl > div:nth-child(2) > div.contentCol > div.results > div.results-holder.allres > div.results-all").MustHTML()
	data, err := ExtractInfFromHTML(html)
	if err != nil {
		return nil, nil
	}
	return data, nil
}
