package matches

import (
	"hltv/models"
	"strings"

	"github.com/PuerkitoBio/goquery"
)

func ExtractInfFromHTML(html string) (data []models.Match, err error) {
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return nil, err
	}

	var matches []models.Match
	matches = []models.Match{}
	doc.Find(".match-wrapper").Each(func(i int, s *goquery.Selection) {

		teams := s.Find(".match-teamname")
		if teams.Length() < 2 {
			return
		}

		eventContainer := s.Find(".match-event").First()
		eventText := strings.TrimSpace(eventContainer.Clone().Children().Remove().End().Text())
		stage := strings.TrimSpace(eventContainer.Find(".match-stage").Text())

		matchURL := ""
		s.Find("a[href^=\"/matches/\"]").EachWithBreak(func(_ int, a *goquery.Selection) bool {
			matchURL, _ = a.Attr("href")
			return false
		})

		match := models.Match{
			MatchID:  s.AttrOr("data-match-id", ""),
			Event:    eventText,
			Stage:    stage,
			TeamA:    strings.TrimSpace(teams.Eq(0).Text()),
			TeamB:    strings.TrimSpace(teams.Eq(1).Text()),
			BO:       strings.TrimSpace(s.Find(".match-meta").Last().Text()),
			IsLive:   s.AttrOr("live", "false") == "true",
			MatchURL: matchURL,
		}

		matches = append(matches, match)
	})

	return matches, nil
}
