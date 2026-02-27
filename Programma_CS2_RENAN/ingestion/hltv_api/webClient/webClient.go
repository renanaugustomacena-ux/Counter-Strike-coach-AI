package webclient

import (
	"time"

	"github.com/go-rod/rod"
)

func StartWebclient() *rod.Browser {

	return rod.New().Timeout(time.Minute).MustConnect()
}
