package main

import (
	"hltv/controllers"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"

	_ "hltv/docs"

	swaggerFiles "github.com/swaggo/files"
	ginSwagger "github.com/swaggo/gin-swagger"
)

func main() {
	router := gin.Default()
	router.Use(cors.Default())
	api := router.Group("/api")
	controllers.HLTVendpoints(api)
	router.GET("/swagger/*any", ginSwagger.WrapHandler(swaggerFiles.Handler))
	router.Run(":8080")
}
