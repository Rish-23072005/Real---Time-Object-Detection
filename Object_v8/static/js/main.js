let isDetecting = true;
        let frameCount = 0;
        let lastTime = performance.now();
        let detectedObjects = 0;
        let confidenceSum = 0;

        // FPS Calculator
        function updateFPS() {
            const now = performance.now();
            const delta = now - lastTime;
            const fps = Math.round(frameCount * 1000 / delta);
            document.getElementById('fps-value').textContent = fps;
            frameCount = 0;
            lastTime = now;
        }

        // Start FPS monitoring
        setInterval(updateFPS, 1000);

        // Monitor frame updates
        const videoFeed = document.getElementById('video-feed');
        videoFeed.onload = function () {
            frameCount++;
            if (isDetecting) {
                // Simulate detection updates (in real implementation, this would come from backend)
                updateDetectionStats();
            }
        };

        function updateDetectionStats() {
            // Simulate random detections (replace with real data from backend)
            const objects = Math.floor(Math.random() * 5) + 1;
            const confidence = Math.random() * 30 + 70;

            detectedObjects += objects;
            confidenceSum += confidence;

            document.getElementById('objects-count').textContent = detectedObjects;
            document.getElementById('avg-confidence').textContent =
                `${(confidenceSum / detectedObjects).toFixed(1)}%`;

            // Add detection to list
            const detectionList = document.getElementById('detection-list');
            const detectionItem = document.createElement('div');
            detectionItem.className = 'detection-item';
            detectionItem.innerHTML = `
                <span>Detected ${objects} objects</span>
                <span>${confidence.toFixed(1)}% confidence</span>
            `;
            detectionList.insertBefore(detectionItem, detectionList.firstChild);

            // Keep list at reasonable length
            if (detectionList.children.length > 50) {
                detectionList.removeChild(detectionList.lastChild);
            }
        }

        // Button Controls
        document.getElementById('start-btn').onclick = function () {
            isDetecting = true;
            this.disabled = true;
            document.getElementById('stop-btn').disabled = false;
        };

        document.getElementById('stop-btn').onclick = function () {
            isDetecting = false;
            this.disabled = true;
            document.getElementById('start-btn').disabled = false;
        };

        document.getElementById('snapshot-btn').onclick = function () {
            // Create a canvas to capture the current frame
            const canvas = document.createElement('canvas');
            canvas.width = videoFeed.width;
            canvas.height = videoFeed.height;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(videoFeed, 0, 0, canvas.width, canvas.height);

            // Download the snapshot
            const link = document.createElement('a');
            link.download = 'detection-snapshot.png';
            link.href = canvas.toDataURL();
            link.click();
        };
