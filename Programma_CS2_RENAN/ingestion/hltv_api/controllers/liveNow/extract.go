package livenow

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

	doc.Find(".match-wrapper.live-match-container").Each(func(i int, s *goquery.Selection) {
		teams := s.Find(".match-teamname")

		if teams.Length() < 2 {
			return
		}

		match := models.Match{
			MatchID:  s.AttrOr("data-match-id", ""),
			Event:    strings.TrimSpace(s.Find(".match-event .text-ellipsis").First().Text()),
			Stage:    strings.TrimSpace(s.Find(".match-stage").Text()),
			TeamA:    strings.TrimSpace(teams.Eq(0).Text()),
			TeamB:    strings.TrimSpace(teams.Eq(1).Text()),
			BO:       strings.TrimSpace(s.Find(".match-meta").Last().Text()),
			IsLive:   strings.Contains(strings.ToLower(s.Find(".match-meta-live").Text()), "live"),
			MatchURL: s.Find("a.match-top").AttrOr("href", ""),
		}

		matches = append(matches, match)
	})
	return matches, nil
}
