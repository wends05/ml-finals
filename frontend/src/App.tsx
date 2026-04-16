import { useCallback, useEffect, useRef, useState } from "react";

interface KioskState {
	prediction: string;
	name: string | null;
	status: number | null;
}

export default function App() {
	const videoRef = useRef<HTMLVideoElement | null>(null);
	const [kioskState, setKioskState] = useState<KioskState>({
		prediction: "Loading...",
		name: null,
		status: null,
	});

	const sendFrameToBackend = useCallback(async () => {
		const video = videoRef.current;
		if (!video) return;

		// Create a hidden canvas to take a "snapshot" of the video
		const canvas = document.createElement("canvas");
		canvas.width = video.videoWidth;
		canvas.height = video.videoHeight;
		const ctx: CanvasRenderingContext2D | null = canvas.getContext("2d");
		if (!ctx) return;
		ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

		// Compress the image to a base64 JPEG (Quality: 0.7 out of 1.0)
		const base64Image = canvas.toDataURL("image/jpeg", 0.7);

		try {
			// Send the frame to FastAPI
			const response = await fetch("http://localhost:8000/api/predict", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ image: base64Image }),
			});

			const data = await response.json();

			console.log("Backend response:", data); // Debugging log
			setKioskState({
				prediction: data.prediction,
				name: data.name,
				status: data.status,
			});
		} catch (error) {
			console.error("Backend unreachable", error);
		}
	}, []);

	useEffect(() => {
		// 1. Request access to the user's webcam
		navigator.mediaDevices
			.getUserMedia({ video: true })
			.then((stream) => {
				if (videoRef.current) {
					videoRef.current.srcObject = stream;
				}
			})
			.catch((err) => console.error("Camera error:", err));

		// 2. Set up a loop to capture and send a frame every 500ms (2 FPS)
		const interval = setInterval(() => {
			sendFrameToBackend();
		}, 500);

		return () => clearInterval(interval); // Cleanup when component unmounts
	}, [sendFrameToBackend]);

	return (
		<div style={{ textAlign: "center", marginTop: "50px" }}>
			<h1>Welcome Kiosk</h1>
			{/* The user sees smooth live video here */}
			{/** biome-ignore lint/a11y/useMediaCaption: ho */}
			<video
				ref={videoRef}
				autoPlay
				playsInline
				style={{ width: "640px", borderRadius: "10px" }}
			/>
			<h2>Status: {kioskState.prediction}</h2>
			<h3>Predicted Person: {kioskState.name || "None"}</h3>
			<h3>Confidence: {kioskState.status}</h3>
		</div>
	);
}
