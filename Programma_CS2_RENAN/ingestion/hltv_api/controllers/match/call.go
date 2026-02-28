package match

import (
	"hltv/models"
	"net/http"

	"github.com/gin-gonic/gin"
)

type Match struct {
	MatchId          string `json:"matchid"`
	MatchDescription string `json:"matchDescription"`
}
type LastMatchSummary struct {
	MapVetoes []models.MapVeto   `json:"mapVetoes"`
	Results   []models.MapResult `json:"results"`
	TeamStats []models.TeamStats `json:"teamStats"`
}

// GetMatches godoc
// @Summary     Get information for a single match
// @Description Using the match ID obtained from /api/last-results, this endpoint returns detailed information about a single match, including maps, results, and team stats.
// @Tags        Match
// @Accept      json
// @Produce     json
// @Param       payload body Match true "Request payload containing the day or other filters"
// @Success     200 {array} LastMatchSummary "List of past match results with map links"
// @Failure     500 {object} models.ErrorResponse "Internal server error"
// @Router      /api/match [post]
func GetMatchData(c *gin.Context) {
	var raw Match
	if err := c.ShouldBindJSON(&raw); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": err.Error(),
		})
		return
	}
	data, err := ExtractData(raw.MatchId, raw.MatchDescription)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, data)
}
