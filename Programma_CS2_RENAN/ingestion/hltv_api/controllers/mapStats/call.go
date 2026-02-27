package mapstats

import (
	"hltv/models"
	"net/http"

	"github.com/gin-gonic/gin"
)

type MapData struct {
	MatchId          string `json:"matchid"`
	MatchDescription string `json:"matchDescription"`
}
type MatchStats struct {
	StatsTeam1 models.TeamStats `json:"StatsTeam1"`
	StatsTeam2 models.TeamStats `json:"StatsTeam2"`
}

// GetMatches godoc
// @Summary     Get stats for a single map from a match
// @Description Using the map ID and description obtained from /match, this endpoint returns detailed statistics for that specific map.
// @Tags        Match
// @Accept      json
// @Produce     json
// @Param       payload body MapData true "Request payload containing the day or other filters"
// @Success     200 {array} MatchStats "List of past match results with map links"
// @Failure     500 {object} models.ErrorResponse "Internal server error"
// @Router      /api/match-stats [post]
func GetMapStats(c *gin.Context) {
	var raw MapData
	if err := c.ShouldBindJSON(&raw); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": err.Error(),
		})
		return
	}
	data, err := ExtractMatches(raw.MatchId, raw.MatchDescription)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": err.Error(),
		})
		return
	}
	c.JSON(http.StatusOK, data)

}
