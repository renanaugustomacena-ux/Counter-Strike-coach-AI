package livenow

import (
	"fmt"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
)

// GetMatches godoc
// @Summary     Matches live now
// @Description Return all matches playing now
// @Tags        Matches
// @Produce     json
// @Success     200 {array} models.Match "List of live matches"
// @Failure     500 {object} models.ErrorResponse "Internal server error"
// @Router      /api/live-now [get]
func CallLiveNow(c *gin.Context) {
	now := fmt.Sprintf("%v-%v-%v", time.Now().Year(), int(time.Now().Month()), time.Now().Day())
	response, err := ExtractLiveNow(now)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": err.Error(),
		})
		return
	}
	c.JSON(http.StatusOK, response)
}
