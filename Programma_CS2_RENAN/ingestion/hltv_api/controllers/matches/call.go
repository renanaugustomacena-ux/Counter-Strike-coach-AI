package matches

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

// GetMatches godoc
// @Summary     Scheduled matches
// @Description Returns all nextMatches within HLTV window context (current day + 5 days). Send only the day as a query parameter. Example: if you want matches for December 16 while in December, send only "16".
// @Tags        Matches
// @Produce     json
// @Success     200 {array} models.Match "List of live matches"
// @Failure     500 {object} models.ErrorResponse "Internal server error"
// @Router      /api/matches:day [get]
func CallMatches(c *gin.Context) {
	date := c.Query("date")
	if date == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"err": "'date' is required",
		})
		return
	}

	response, err := ExtractMatches(date)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": err.Error(),
		})
		return
	}
	c.JSON(http.StatusOK, response)
}
