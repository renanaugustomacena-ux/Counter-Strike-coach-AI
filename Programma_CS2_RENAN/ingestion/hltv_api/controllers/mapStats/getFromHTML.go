package mapstats

import (
	"hltv/models"
	"strconv"
	"strings"

	"github.com/PuerkitoBio/goquery"
)

func ExtractInfFromHTML(html string) (data models.TeamStats, err error) {
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return models.TeamStats{}, err
	}

	var stats models.TeamStats

	table := doc.Find("table.stats-table").First()

	teamName := strings.TrimSpace(
		table.Find("th.st-teamname").
			First().
			Clone().
			Children().
			Remove().
			End().
			Text(),
	)

	var players []models.Player

	table.Find("tbody tr").Each(func(_ int, tr *goquery.Selection) {
		playerName := strings.TrimSpace(tr.Find("td.st-player a").Text())
		if playerName == "" {
			return
		}

		kills := strings.TrimSpace(
			tr.Find("td.st-kills.traditional-data").
				Clone().
				Children().
				Remove().
				End().
				Text(),
		)

		deaths := strings.TrimSpace(
			tr.Find("td.st-deaths.traditional-data").
				Clone().
				Children().
				Remove().
				End().
				Text(),
		)

		kd := kills + "-" + deaths

		swingText := strings.TrimSpace(tr.Find("td.st-roundSwing").Text())
		swingText = strings.ReplaceAll(swingText, "%", "")
		swingText = strings.ReplaceAll(swingText, "+", "")
		swing, _ := strconv.ParseFloat(swingText, 64)

		adrText := strings.TrimSpace(tr.Find("td.st-adr.traditional-data").First().Text())
		adr, _ := strconv.ParseFloat(adrText, 64)

		kastText := strings.TrimSpace(tr.Find("td.st-kast.traditional-data").First().Text())
		kastText = strings.ReplaceAll(kastText, "%", "")
		kast, _ := strconv.ParseFloat(kastText, 64)

		ratingText := strings.TrimSpace(tr.Find("td.st-rating").First().Text())
		rating, _ := strconv.ParseFloat(ratingText, 64)

		players = append(players, models.Player{
			PlayerName: playerName,
			KD:         kd,
			Swing:      swing,
			ADR:        adr,
			KAST:       kast,
			Rating30:   rating,
		})
	})

	stats = models.TeamStats{
		TeamName:     teamName,
		PlayersStats: players,
	}

	return stats, nil
}
