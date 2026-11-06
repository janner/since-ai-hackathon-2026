# LUMI hackathonissa: mitä käyttöoikeus avaa

Tarkistettu 4.11.2026. Lähteet: docs.lumi-supercomputer.eu (hardware, partitions, storage, billing, webui, laif), sinceai.ai/hackathon-2026/guide + /resources, lumi-ai-factory.github.io/LUMI_AIF_Onboarding.

## Mitä Since AI antaa

- CSC/LUMI-rekisteröinti oli vapaaehtoinen, takaraja pe 30.10.2026.
- Käyttö on jaettu hackathon-projekti, vain hackathon-työhön. Uusi CSC-tunnus vaatii oman organisaation sähköpostin (Laurea käy).
- Mukana myös Aitta: avoimien mallien inferenssipalvelu LUMIn päällä, web-käyttöliittymä + OpenAI-yhteensopiva API.
- LUMI AI Factoryn asiantuntijat ovat paikan päällä koko viikonlopun.
- Omakohtainen kiintiö 4.11.2026 (jaettu hackathon-projekti): CPU 49 898 core-h jäljellä (50 000), GPU 4 581 GPU-h jäljellä (5 000, käytetty 418), tallennus 5 159 TiB-h jäljellä (10 000, käytetty 4 840). Palkit näyttävät jäljellä olevan osuuden, ei käytettyä.

## Rauta

| Osa | Koko | Huom |
|---|---|---|
| LUMI-G | 2978 nodea, 4× AMD MI250X = 8 GCD/node, 128 GB HBM, 512 GB RAM | 379,7 PFlop/s HPL. ROCm, ei CUDA. |
| LUMI-C | 2048 nodea, 2× EPYC 7763, 128 corea/node, 256/512/1024 GiB | Batch-CPU, ei omaa levyä. |
| LUMI-D | 16 nodea, 4 TiB muisti; 8:ssa 8× Nvidia A40 | Visualisointiin, ei laskentaan. |
| LUMI-K | 28 worker-nodea, OKD/Kubernetes | Eri allokaatio, ei kuulu hackathon-projektiin. |

Yhteensä LUMI-G:ssä on 23 824 GCD:tä. Yksi MI250X = 2 GCD = 128 GB.

## Kiintiöt ja laskutus

- GPU-tunti = yksi MI250X (2 GCD) tunniksi. `standard-g`: koko node aina, 4 GPU-tuntia/node/tunti.
- `small-g`: voi varata yksittäisiä GCD:itä, laskutus 0,5 × GCD × tunti. Max 4 nodea, 3 vrk.
- `dev-g`: testaus, 30 min – 2 h, max 16 nodea.
- `standard-g` ja `standard`: 2 vrk. `largemem`: 1 node, 4 TB.
- Levy: home 20 GB, project 50 GB (kasvatettavissa 500 GB), scratch 50 TB, flash 2 TB (3× hinta), LUMI-O 150 TB (0,25× hinta).
- Ei varmuuskopioita. Data poistuu 90 vrk projektin päättymisestä.

## Aitta: nopein tapa saada LUMI käyttöön

- API: `https://aitta-api.csc.fi/openai/v1`, token `https://aitta-auth.csc.fi/myToken` (valitse projekti, voimassa 90 vrk).
- Chat completions ja embeddings. Osa malleista lukee myös kuvia.
- Malliesimerkkejä: `openai/gpt-oss-120b`, `LumiOpen/Llama-Poro-2-70B-Instruct`, `Qwen/Qwen3-Coder-Next`. Lista: `GET /model`, ajossa olevat: `GET /worker`.
- Kapasiteetti 2 LUMI-G nodea = 16 GCD jaettuna kaikkien käyttäjien kesken. Malli voi olla offline, ensimmäinen pyyntö odottaa latausta. Ei tuotantokäyttöön, ei saatavuustakuuta.
- Rate limit per minuutti; `429` → odota minuutti.

```python
import openai
client = openai.OpenAI(api_key="<token>", base_url="https://aitta-api.csc.fi/openai/v1")
client.chat.completions.create(model="openai/gpt-oss-120b",
    messages=[{"role": "user", "content": "Hei"}])
```

## Oma ajo LUMI-G:llä

Valmis kontti, ei asennuksia Lustreen:

```bash
module purge
module load Local-LAIF lumi-aif-singularity-bindings
export SIF=/appl/local/laifs/containers/lumi-multitorch-latest.sif
srun -A <projekti> -p dev-g -n 1 --gpus-per-task=1 singularity run $SIF \
  python -c "import torch; print(torch.cuda.device_count())"
```

Kontissa on PyTorch, DeepSpeed, Flash Attention, Megatron-LM, vLLM, bitsandbytes. Koko pino: lumi-multitorch-full. Intermediate-kuvista voi rakentaa oman (esim. JAX).

LUMI AI Guide (github.com/Lumi-supercomputer/LUMI-AI-Guide) sisältää MM. LoRA-fine-tunen ja vLLM-inferenssin reseptit.

## Selain käyttöliittymä (ei SSH:ta)

www.lumi.csc.fi: tiedostot, shell, compute node shell, Jupyter (myös `lumi-multitorch`), VS Code, Desktop, MLflow, TensorBoard, jonot ja kiintiöt.

## Mihin tätä oikeasti kannattaa käyttää 48 tunnissa

1. Aitta = oletus. RAG, agentti, luokittelu, OCR-tekstin jälkikäsittely, evaluointi. Ei asennuksia, ei jonoa omalle työlle.
2. LUMI-G vain jos haaste vaatii oman mallin fine-tunea tai inferenssiä omalla painolla. LoRA pienellä mallilla onnistuu, mutta vie aikaa: dev-g-testi ensin, sitten small-g 1–2 GCD.
3. LUMI-C/D kun data on iso: 50 TB scratch, 4 TB muisti, batch-OCR tai aikasarja-ajo.
4. LUMI-O jakaa artefaktit julkisella URLilla: `https://<projektinumero>.lumidata.eu/<bucket>`. Web-käyttöliittymän Cloud storage -app tekee bucketit.
5. Demo pyörii läppärillä ja kutsuu Aittaa. LUMI ei hostaa julkista demoa.

## Sudenkuopat

- ROCm: CUDA-koodi ei käänny LUMI-G:llä. A40:t LUMI-D:ssä ovat visualisointiin, niillä laskeminen voi johtaa tilin sulkemiseen.
- Jaettu projekti: BU:t voivat loppua kesken. Tarkista `lumi-allocations` ennen isoa ajoa.
- Jono: 48 h aikana small-g voi odottaa. Testaa dev-g:llä aikaisin.
- Älä asenna pieniä tiedostoja Lustreen (pip/conda). Käytä konttia.
- Sensitiivinen data: GDPR ja erillinen sopimus. Ei henkilötietoja LUMI:in ilman lupaa. Sama linja kuin privacy routingissa.
- En tarkistanut, onko laskentasolmuilla ulospäin menevä verkkoyhteys. Älä suunnittele ajoa, joka lataa riippuvuuksia ajon aikana.

## Linkit

- docs.lumi-supercomputer.eu
- aitta.csc.fi, aitta-api.csc.fi/docs
- lumi-ai-factory.github.io/LUMI_AIF_Onboarding (8 lukua, ~8 h; lue tiivistetysti luvut 2–5 ja 7)
- github.com/Lumi-supercomputer/LUMI-AI-Guide
- status.lumi.csc.fi
