package match

import (
	"fmt"
	"hltv/models"
	"regexp"
	"strconv"
	"strings"

	"github.com/PuerkitoBio/goquery"
)

func parseFloat(val string) float64 {
	val = strings.TrimSpace(val)
	val = strings.ReplaceAll(val, "%", "")
	val = strings.ReplaceAll(val, "+", "")

	f, _ := strconv.ParseFloat(val, 64)
	return f
}

func parsePercent(val string) float64 {
	return parseFloat(val)
}
func ExtractMapsStats(html string) ([]models.TeamStats, error) {
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return nil, err
	}

	var teams []models.TeamStats

	doc.Find(".stats-content table.table.totalstats").EachWithBreak(
		func(i int, table *goquery.Selection) bool {

			var team models.TeamStats

			team.TeamName = strings.TrimSpace(
				table.Find(".header-row .teamName").First().Text(),
			)

			table.Find("tr").Each(func(i int, row *goquery.Selection) {
				if row.HasClass("header-row") {
					return
				}

				var player models.Player

				player.PlayerName = strings.TrimSpace(
					row.Find(".player-nick").First().Text(),
				)

				player.KD = strings.TrimSpace(
					row.Find("td.kd.traditional-data").First().Text(),
				)

				player.Swing = parseFloat(
					row.Find("td.roundSwing").First().Text(),
				)

				player.ADR = parseFloat(
					row.Find("td.adr.traditional-data").First().Text(),
				)

				player.KAST = parseFloat(
					row.Find("td.kast.traditional-data").First().Text(),
				)

				player.Rating30 = parseFloat(
					row.Find("td.rating").First().Text(),
				)

				team.PlayersStats = append(team.PlayersStats, player)
			})

			teams = append(teams, team)

			return len(teams) < 2
		},
	)

	return teams, nil
}

func ExtractMapsResultData(html string) (data []models.MapResult, err error) {
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return nil, err
	}

	doc.Find(".flexbox-column .mapholder").Each(func(i int, mapholder *goquery.Selection) {

		var result models.MapResult
		link := mapholder.
			Find(".results-center .results-center-stats a.results-stats").
			First()

		href, ok := link.Attr("href")
		if !ok {
			return
		}
		result.Url = fmt.Sprintf("https://www.hltv.org%v", href)
		result.MapName = strings.TrimSpace(
			mapholder.Find(".mapname").First().Text(),
		)

		left := mapholder.Find(".results-left").First()
		result.Team1.TeamName = strings.TrimSpace(
			left.Find(".results-teamname").First().Text(),
		)

		if left.HasClass("won") {
			result.Team1.WonMaps = 1
		} else {
			result.Team1.WonMaps = 0
		}

		right := mapholder.Find(".results-right").First()
		result.Team2.TeamName = strings.TrimSpace(
			right.Find(".results-teamname").First().Text(),
		)

		if right.HasClass("won") {
			result.Team2.WonMaps = 1
		} else {
			result.Team2.WonMaps = 0
		}

		data = append(data, result)
	})

	return data, nil
}

func ExtractMapsVet(html string) (data []models.MapVeto, err error) {
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return nil, err
	}

	var mapChoices []models.MapVeto
	doc.Find(".padding").Each(func(i int, s *goquery.Selection) {
		s.Children().Each(func(j int, item *goquery.Selection) {
			text := strings.TrimSpace(item.Text())
			text = strings.ReplaceAll(text, "\n", " ")
			text = strings.Join(strings.Fields(text), " ")

			re := regexp.MustCompile(`^(\d+)\.\s+(.+?)\s+(removed|picked)\s+(.*)$`)
			match := re.FindStringSubmatch(text)

			if len(match) == 5 {
				mapChoices = append(mapChoices, models.MapVeto{
					TeamName:   match[2],
					TeamChoice: match[3],
					MapName:    match[4],
				})
				return
			}

			reLeft := regexp.MustCompile(`^(.*?)\s+was left over$`)
			left := reLeft.FindStringSubmatch(text)
			if len(left) == 2 {
				mapChoices = append(mapChoices, models.MapVeto{
					TeamChoice: "decider",
					MapName:    left[1],
				})
			}
		})
	})

	return mapChoices, nil
}
