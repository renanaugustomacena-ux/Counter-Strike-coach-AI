
# HLTV API Open Source Project
Fetches public data from HLTV and allows you to extend it with additional endpoints. Please submit updates via pull requests for review.

This API can be used by cloning the repository and running it. Access Swagger at http://localhost:8080/swagger/index.html to see all endpoints. If you submit a pull request, make sure any new or updated endpoints are fully documented in Swagger.
## Installation

git clone https://github.com/Gabrielcnetto/HLTV-api.git

```bash
  cd HLTV-api
  go run main.go
```

## Endpoints

You can access all available endpoints using Swagger or by checking the `/controllers/endpoints.go` file.



```bash
	router.GET("/live-now", livenow.CallLiveNow)
	router.GET("/matches", matches.CallMatches)
	router.GET("/last-results", results.CallResults)
	router.POST("/match", match.GetMatchData)
	router.POST("/match-stats", mapstats.GetMapStats)
	router.POST("/heat-map", heatmapmatch.CallHeatMapMatch)
```

## Example usage Get matches live now

**Request Example using `curl`:**  
```bash
curl -X GET http://localhost:8080/api/live-now

response example:

[
  {
    "matchId": "12345",
    "team1": "Team A",
    "team2": "Team B",
    "map": "Dust2",
    "score": "10-5",
    "time": "15:30"
  },
  {
    "matchId": "12346",
    "team1": "Team C",
    "team2": "Team D",
    "map": "Mirage",
    "score": "3-12",
    "time": "16:00"
  }
]
```
## Get Map Stats

Fetch detailed statistics for a single map from a match. Use the `matchId` and `matchDescription` obtained from the `/match` endpoint.

**Endpoint:**  

**Request Example using `curl`:**  
```bash
curl -X POST http://localhost:8080/api/match-stats \
-H "Content-Type: application/json" \
-d '{
  "matchid": "215455",
  "matchDescription": "furia-vs-natus-vincere"
}'

response example:

{
    "StatsTeam1": {
        "TeamName": "FaZe",
        "PlayersStats": [
            {
                "PlayerName": "Twistzz",
                "KD": "20-10",
                "Swing": 7.5,
                "ADR": 91.3,
                "KAST": 85.7,
                "Rating30": 1.87
            },
            {
                "PlayerName": "jcobbb",
                "KD": "17-10",
                "Swing": 6.19,
                "ADR": 102.6,
                "KAST": 90.5,
                "Rating30": 1.66
            },
            {
                "PlayerName": "broky",
                "KD": "20-13",
                "Swing": -0.1,
                "ADR": 90.7,
                "KAST": 95.2,
                "Rating30": 1.37
            },
            {
                "PlayerName": "karrigan",
                "KD": "12-12",
                "Swing": -0.29,
                "ADR": 53.3,
                "KAST": 81,
                "Rating30": 1
            },
            {
                "PlayerName": "frozen",
                "KD": "13-14",
                "Swing": -2.45,
                "ADR": 87.6,
                "KAST": 71.4,
                "Rating30": 0.97
            }
        ]
    },
    "StatsTeam2": {
        "TeamName": "Natus Vincere",
        "PlayersStats": [
            {
                "PlayerName": "makazze",
                "KD": "14-16",
                "Swing": 0.38,
                "ADR": 78.6,
                "KAST": 76.2,
                "Rating30": 1.1
            },
            {
                "PlayerName": "b1t",
                "KD": "15-16",
                "Swing": -2.86,
                "ADR": 74.7,
                "KAST": 61.9,
                "Rating30": 0.91
            },
            {
                "PlayerName": "Aleksib",
                "KD": "10-15",
                "Swing": -0.81,
                "ADR": 60,
                "KAST": 66.7,
                "Rating30": 0.8
            },
            {
                "PlayerName": "w0nderful",
                "KD": "12-18",
                "Swing": -3.03,
                "ADR": 52.7,
                "KAST": 52.4,
                "Rating30": 0.72
            },
            {
                "PlayerName": "iM",
                "KD": "8-17",
                "Swing": -4.53,
                "ADR": 53.6,
                "KAST": 61.9,
                "Rating30": 0.6
            }
        ]
    }
}
```
## Requirements
- Go 1.20+ (or latest stable version)
- Git
## Used Packages

 - [ROD Golang](https://github.com/go-rod/rod)
 - [GOquery](https://github.com/PuerkitoBio/goquery)
 - [GIN](https://github.com/gin-contrib/cors)
 - [Swagger](https://github.com/swaggo/swag)
## Feedback

Don't hesitate to add new features and endpoints! Please keep the code clean and well-structured, and make sure all new endpoints are properly documented. I would love to see the new features you create!

## Authors

- [Github](https://github.com/Gabrielcnetto)
- [X (Ex twitter)](https://x.com/gcn10x)
[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/Gabrielcnetto/HLTV-api/blob/main/LICENSE)
