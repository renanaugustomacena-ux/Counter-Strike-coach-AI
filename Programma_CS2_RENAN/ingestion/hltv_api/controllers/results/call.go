package results

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

// GetMatches godoc
// @Summary     Last available matches result
// @Description Returns all available results on /results from hltv
// @Tags        Results
// @Produce     json
// @Success     200 {array} models.Results "List of live matches"
// @Failure     500 {object} models.ErrorResponse "Internal server error"
// @Router      /api/last-results [POST]
func CallResults(c *gin.Context) {
	response, err := ExtractResults()
	if err != nil {
		c.JSON(http.StatusBadRequest, err.Error())
		return
	}
	c.JSON(http.StatusOK, response)
}
