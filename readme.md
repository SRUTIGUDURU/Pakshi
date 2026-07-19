**🪶 Pakshi - Connecting Artisans to Intent**

**Voice-first marketplace where demand creates supply.**  
_Made for Meesho Hackathon 2026 - Round 3 Prototype._

**Table of Contents**

- The Problem
- Our Solution
- Key Features
- Tech Stack
- Live Demo
- Setup & Run Locally
- File Structure
- Usage Walkthrough
- Future Roadmap

**The Problem**

- **43 lakh** handloom weavers in India - **70% are women**.
- Average weaver earns **< ₹400** per saree, while retail price is ~₹1800.
- **Middlemen extract up to 60%** of the final value.
- Buyers struggle to describe _"feel"_ - weavers think in **craft techniques**, not catalogues.
- Existing marketplaces demand **English & tech literacy** - barriers for both rural artisans and tier‑2+ buyers.

**Our Solution**

**Pakshi** is a **voice-first, intent-driven marketplace** where demand creates supply.  
We operate on a **made-to-order** model, eliminating inventory risk and dead stock.  
**No English required. No typing. Just speak.**

I built a **fully functional prototype** in 7 days covering the **end-to-end lifecycle**:

- **Buyer** intuitively discovers, selects, and orders.
- **Weaver** seamlessly receives, accepts, and updates via voice.
- **Rejected pieces** transition to a **wholesale resale channel** (OOAK) - zero waste.

**Key Features**

**Buyer Portal**

- **Bilingual voice & text** (Hindi / English).
- **Agentic intent matching** - interprets occasion, budget, and feel.
- **Rich swatches** with real images, price, weaver details, delivery.
- **Order tracking** - "In Production" → "Awaiting Approval" → "Completed".
- **Approve/reject** final fabric photos - rejection moves to OOAK.

**Weaver Dashboard**

- **Dedicated profile & order management**.
- **Hands-free voice controls** - Accept/Reject/Show Buyer (crucial for loom workers).
- **Minimum base price** - orders below threshold are flagged.
- **Simulated order broadcast** - test the flow.
- **Photo upload & send** to buyer for approval.

**Weaver Onboarding (Zero Friction)**

- **Voice-assisted form** - speaks name, village, weave, phone → auto‑parsed.
- **One‑click location** - GPS + IP fallback fills village/cluster and state.
- **Instant profile publishing** - goes live on the network.

**One of a Kind (OOAK) - Zero Waste**

- Rejected orders are automatically listed at **65% of original price**.
- **Weaver recovers partial value** - no dead stock.
- **Buyers get unique pieces at wholesale rates**.
- **No reverse logistics, no inventory loss.**

**Tech Stack**

| Component          | Technology                                                     |
| ------------------ | -------------------------------------------------------------- |
| **Frontend & UI**  | Streamlit (Python)                                             |
| **Speech-to-Text** | speech_recognition (Google Speech API)                         |
| **Text-to-Speech** | edge-tts (Microsoft Edge)                                      |
| **Agent Logic**    | Custom Python - rule-based reasoning using JSON knowledge base |
| **Data Storage**   | Local JSON files (weaver_profiles, fabric_swatches, ontology)  |
| **Geolocation**    | Nominatim (OSM) reverse geocoding + IP‑based fallback          |
| **Deployment**     | Streamlit Cloud / localhost                                    |

All tools are **free/open-source** - no paid APIs used in the prototype.

**Live Demo**

Try the deployed version: [**https://pakshi.streamlit.app**](https://pakshi.streamlit.app/)

_Note: For voice & GPS features, allow microphone and location permissions when prompted. Best experienced on Chrome/Edge._

**Setup & Run Locally**

**Prerequisites**

- **Python 3.8+**
- **pip**
- **Internet connection** (for voice APIs and image loading)

**1\. Clone the repository**

bash

git clone <https://github.com/SRUTIGUDURU/pakshi.git>

cd pakshi

**2\. Install dependencies**

bash

pip install -r requirements.txt

If pydub or audio codecs are needed, install system packages (e.g., ffmpeg):

- **Ubuntu/Debian:** sudo apt-get install ffmpeg
- **Mac:** brew install ffmpeg
- **Windows:** Download ffmpeg and add to PATH.

**3\. Run the app**

bash

streamlit run app.py

The app will open at <http://localhost:8501>.

**File Structure**

text

pakshi/

├── app.py # Main Streamlit application

├── agent.py # Core agent logic (intent matching, orchestration)

├── intent_parser.py # Parses user intent from text

├── retrieval.py # Retrieval of swatches & weavers

├── setup_chromadb.py # ChromaDB setup (optional vector DB)

├── fabric_ontology.json # Fabric taxonomy (fabric types, weaves, etc.)

├── fabric_swatches.json # 100+ swatches with images & metadata

├── weaver_profiles.json # Weaver profiles (50+ pre‑loaded)

├── requirements.txt # Python dependencies

├── packages.txt # System packages (e.g., ffmpeg)

└── README.md # This file

**Usage Walkthrough**

**For Buyers**

- Open the **Buyer Portal** tab.
- Click the microphone icon and speak your requirement (e.g., "I want a Kanjivaram silk saree under ₹10,000").
- The agent will display 2-3 matching swatches with images and details.
- Select an option - your order is confirmed and broadcast to weavers.
- Track order status and approve/reject final fabric photos.

**For Weavers**

- Switch to the **Weaver Dashboard** tab.
- Select your profile from the dropdown.
- Use the microphone to give commands:
  - "Accept first order" or "Accept order 2847"
  - "Reject first order"
  - "Show buyer" (send photo)
- Upload a photo and click **"Send Photo for Buyer Approval"**.

**For Onboarding (New Weavers)**

- Go to the **Weaver Onboarding** tab.
- Click the microphone and speak your name, village, weave, and phone.
- Click **"Give Location"** to auto‑fill village and state (uses GPS or IP fallback).
- Review and submit - profile goes live instantly.

**One of a Kind (OOAK)**

- Visit the **One of a Kind** tab to browse rejected pieces at wholesale prices.
- Click **"Buy Now"** to add to cart (demo flow).

**Future Roadmap**

**Immediate (post‑hackathon)**

- Replace local JSON with real database (PostgreSQL).
- Integrate Meesho's WhatsApp API for weaver communication.
- Scale to 500+ weavers & 1000+ swatches.
- Add all 22 Indian languages.

**Medium‑term**

- Fine‑tune open‑source LLM (Llama 3) for deeper agent reasoning.
- Automated logistics & payment integration.

**Long‑term**

- AI‑powered design suggestions.
- Fraud detection & quality scoring.
- Full Meesho order management & logistics integration.

**Acknowledgments**

- Meesho for the inspiration and platform.
- Mentors for their invaluable guidance during the hackathon.
