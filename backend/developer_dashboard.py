from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter(tags=["ATHENA Control Center"])


@router.get("/control", response_class=HTMLResponse)
async def control_center():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>ATHENA Control Center</title>
    <style>
        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #0b0f19;
            color: #ffffff;
        }
        header {
            background: #111827;
            padding: 20px;
            border-bottom: 1px solid #263244;
        }
        h1 {
            margin: 0;
            font-size: 28px;
        }
        .container {
            padding: 24px;
            max-width: 1200px;
            margin: auto;
        }
        .card {
            background: #111827;
            border: 1px solid #263244;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }
        button {
            background: #2563eb;
            color: white;
            border: none;
            padding: 12px 18px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 15px;
            margin-right: 8px;
        }
        button:hover {
            background: #1d4ed8;
        }
        input, textarea {
            width: 100%;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #374151;
            background: #0f172a;
            color: white;
            font-size: 15px;
            box-sizing: border-box;
        }
        textarea {
            min-height: 90px;
        }
        pre {
            background: #020617;
            padding: 16px;
            border-radius: 8px;
            overflow-x: auto;
            white-space: pre-wrap;
        }
        .status {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }
        .pill {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 999px;
            padding: 8px 14px;
        }
    </style>
</head>
<body>
    <header>
        <h1>ATHENA Control Center</h1>
        <p>Executive AI Operating System</p>
    </header>

    <div class="container">

        <div class="card">
            <h2>System Status</h2>
            <button onclick="healthCheck()">Health Check</button>
            <button onclick="rebuildMemory()">Rebuild Semantic Memory</button>
            <div id="status" class="status" style="margin-top:16px;"></div>
        </div>

        <div class="card">
            <h2>Ask ATHENA</h2>
            <textarea id="question" placeholder="Ask ATHENA a business question...">What warranty is required for the tactical boots?</textarea>
            <br><br>
            <button onclick="askAthena()">Ask ATHENA</button>
        </div>

        <div class="card">
            <h2>Search Memory</h2>
            <input id="searchQuery" placeholder="Search ATHENA memory..." value="military combat footwear">
            <br><br>
            <button onclick="searchMemory()">Search</button>
        </div>

        <div class="card">
            <h2>Result</h2>
            <pre id="result">Waiting...</pre>
        </div>

    </div>

    <script>
        const API_BASE = "";

        function showResult(data) {
            document.getElementById("result").textContent = JSON.stringify(data, null, 2);
        }

        async function healthCheck() {
            const response = await fetch(API_BASE + "/health");
            const data = await response.json();

            const statusDiv = document.getElementById("status");
            statusDiv.innerHTML = "";

            Object.keys(data).forEach(key => {
                const pill = document.createElement("div");
                pill.className = "pill";
                pill.textContent = key + ": " + data[key];
                statusDiv.appendChild(pill);
            });

            showResult(data);
        }

        async function rebuildMemory() {
            const response = await fetch(API_BASE + "/engine/008/rebuild", {
                method: "POST"
            });
            const data = await response.json();
            showResult(data);
        }

        async function askAthena() {
            const question = document.getElementById("question").value;

            const formData = new FormData();
            formData.append("question", question);
            formData.append("limit", "5");

            const response = await fetch(API_BASE + "/engine/009/answer", {
                method: "POST",
                body: formData
            });

            const data = await response.json();
            showResult(data);
        }

        async function searchMemory() {
            const query = encodeURIComponent(document.getElementById("searchQuery").value);

            const response = await fetch(API_BASE + "/engine/008/search?query=" + query);
            const data = await response.json();

            showResult(data);
        }

        healthCheck();
    </script>
</body>
</html>
"""