package heatmapmatch

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

type MapData struct {
	MatchId          string `json:"matchid"`
	MatchDescription string `json:"matchDescription"`
}

// CallHeatMapMatch godoc
// @Summary     Get heatmap image for a match
// @Description Returns the heatmap image (PNG) for a match based on the provided MatchId and MatchDescription.
// @Tags        Heatmap
// @Accept      json
// @Produce     json
// @Param       payload body MapData true "Payload with MatchId and MatchDescription"
// @Success     200 {object} models.HeatmapResponse "Heatmap image URL"
// @Failure     400 {object} models.ErrorResponse "Internal server error"
// @Router      /api/heatmap [post]
func CallHeatMapMatch(c *gin.Context) {
	var raw MapData
	if err := c.ShouldBindJSON(&raw); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": err.Error(),
		})
		return
	}
	data := GetHeatMap(raw.MatchId, raw.MatchDescription)
	c.Data(
		200,
		"image/png",
		data,
	)
}
