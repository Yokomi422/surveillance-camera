package main

import (
	"encoding/json"
	"io"
	"log"
	"net/http"
	"os"
	"sync"
)

type DetectionData struct {
	Status string `json:"status"`
	Detail string `json:"detail"`
}

var (
	latestFrameMutex sync.RWMutex
	latestFramePath  = "./latest_frame.jpg"

	latestDetection *DetectionData
	detectionMutex  sync.RWMutex
)

func uploadFrameHandler(w http.ResponseWriter, r *http.Request) {
	// 既存のコードそのまま
	if r.Method != http.MethodPost {
		http.Error(w, "Invalid request method", http.StatusMethodNotAllowed)
		log.Println("Error: Invalid request method")
		return
	}

	err := r.ParseMultipartForm(32 << 20) // 32MB
	if err != nil {
		http.Error(w, "Failed to parse form data", http.StatusBadRequest)
		log.Printf("Error parsing form data: %v", err)
		return
	}

	// ファイルを取得
	file, _, err := r.FormFile("image")
	if err != nil {
		http.Error(w, "Failed to read image", http.StatusBadRequest)
		log.Printf("Error reading image: %v", err)
		return
	}
	defer file.Close()

	// 画像を保存
	latestFrameMutex.Lock()
	f, err := os.OpenFile(latestFramePath, os.O_WRONLY|os.O_CREATE, 0666)
	if err != nil {
		latestFrameMutex.Unlock()
		http.Error(w, "Failed to save image", http.StatusInternalServerError)
		log.Printf("Error saving image: %v", err)
		return
	}
	_, err = io.Copy(f, file)
	f.Close()
	latestFrameMutex.Unlock()

	if err != nil {
		http.Error(w, "Failed to save image", http.StatusInternalServerError)
		log.Printf("Error saving image: %v", err)
		return
	}

	w.WriteHeader(http.StatusOK)
	log.Println("Frame received and saved")
}

func getFrameHandler(w http.ResponseWriter, r *http.Request) {
	latestFrameMutex.RLock()
	defer latestFrameMutex.RUnlock()

	if _, err := os.Stat(latestFramePath); os.IsNotExist(err) {
		http.Error(w, "No frame available", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "image/jpeg")
	http.ServeFile(w, r, latestFramePath)
}

func notificationHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Invalid request method", http.StatusMethodNotAllowed)
		log.Println("Error: Invalid request method")
		return
	}

	err := r.ParseMultipartForm(32 << 20) 
	if err != nil {
		http.Error(w, "Failed to parse form data", http.StatusBadRequest)
		log.Printf("Error parsing form data: %v", err)
		return
	}

	status := r.FormValue("status")
	detail := r.FormValue("detail")
	data := DetectionData{
		Status: status,
		Detail: detail,
	}

	file, _, err := r.FormFile("image")
	if err != nil {
		http.Error(w, "Failed to read image", http.StatusBadRequest)
		log.Printf("Error reading image: %v", err)
		return
	}
	defer file.Close()

	latestFrameMutex.Lock()
	f, err := os.OpenFile(latestFramePath, os.O_WRONLY|os.O_CREATE, 0666)
	if err != nil {
		latestFrameMutex.Unlock()
		http.Error(w, "Failed to save image", http.StatusInternalServerError)
		log.Printf("Error saving image: %v", err)
		return
	}
	_, err = io.Copy(f, file)
	f.Close()
	latestFrameMutex.Unlock()

	if err != nil {
		http.Error(w, "Failed to save image", http.StatusInternalServerError)
		log.Printf("Error saving image: %v", err)
		return
	}

	detectionMutex.Lock()
	latestDetection = &data
	detectionMutex.Unlock()

	w.WriteHeader(http.StatusOK)
	log.Println("Notification received and saved")
}

func getDetectionHandler(w http.ResponseWriter, r *http.Request) {
	detectionMutex.RLock()
	data := latestDetection
	detectionMutex.RUnlock()

	if data == nil {
		http.Error(w, "No detection data available", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(data)
}

func main() {
	http.HandleFunc("/upload_frame", uploadFrameHandler)
	http.HandleFunc("/get_frame", getFrameHandler)
	http.HandleFunc("/notification", notificationHandler) 
	http.HandleFunc("/get_detection", getDetectionHandler)
	log.Println("Server started at :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}