# GeoSR-4 — Decision Log

Har major decision yahan likha jayega, saath mein uske peeche ka reason (why), consider kiye gaye alternatives, aur status. Naya decision aane par purane ko edit mat karo — naya entry add karo (agar koi decision revise/reverse hota hai, to us purane entry ka status update karke, uska reference dete hue naya entry banao).

Format: har entry ke paas ID, date, decision, reasoning, alternatives, status hona chahiye.

---

## D001 — Adopt GeoSR-4 PRD as the baseline plan
**Date:** 2026-09-07
**Decision:** `GeoSR-4-Complete-PRD.md` ko project ka baseline reference maana jayega — problem framing, phased build order (Phase 0–13), aur architecture layers usi se follow honge, jab tak koi decision explicitly usse deviate na kare.
**Reasoning:** PRD correctly identifies ki yeh problem sirf "image sharpen karna" nahi hai — asli challenge hai reconstruction + uncertainty + validation, kyunki kuch fine detail model se inferred hota hai, directly observed nahi. Yeh distinction hi project ka strongest scientific point ban sakta hai. PRD ka progressive build order (Bicubic → EDSR/RCAN → SwinIR → custom GeoSR-4) overengineering se bachata hai aur ek ablation-study story bhi deta hai jo judges ke saamne scientifically defensible hai.
**Alternatives considered:** Directly jump to a complex transformer+diffusion architecture — reject kiya kyunki PRD khud isse "Risk 6: Overengineering" bolta hai, aur hackathon timeline mein yeh risk zyada hai reward se.
**Status:** Accepted.

---

## D002 — Use SEN2NAIP dataset for training/validation, prioritize `cross-sensor` split over `synthetic` shards
**Date:** 2026-09-07/08
**Decision:** Training/validation data ke liye `isp-uv-es/SEN2NAIP` (Hugging Face) dataset use karenge. Pehle sirf `cross-sensor/cross-sensor.zip` (real Sentinel-2 ↔ NAIP pairs) use karenge; `synthetic/synthetic_01.zip`–`synthetic_18.zip` shards ko tab tak nahi chhuenge jab tak pipeline end-to-end kaam nahi kar raha aur genuinely zyada training volume chahiye.
**Reasoning:**
- Cross-sensor split mein exactly PRD ke MVP spec se match karta hai: LR (Sentinel-2) = 10 m, HR (NAIP-derived) = 2.5 m → scale factor 4×, jo PRD ke "<4m" target ko almost exactly satisfy karta hai.
- Bands RGBNIR hain, jo PRD ke MVP band choice (B2/B3/B4/B8) se directly map karte hain.
- Yeh **real** paired data hai (Strategy A, PRD §43), synthetic degradation (Strategy B) nahi — scientifically stronger starting point, PRD ki apni recommendation ke mutabik ("best approach: synthetic pehle, phir real data se validate/fine-tune").
- Cross-sensor pairs ko dataset authors ne <1 day acquisition-gap filter se banaya hai, jo PRD ke apne "Risk 2 — Misalignment" concern ko kaafi had tak address karta hai.
- File size: `cross-sensor.zip` sirf ~2.1 GB hai (confirmed via HF API), jabki poora repo (18 synthetic shards + cross-sensor) ~180 GB ka hai. Poora dataset download karna is stage par unnecessary aur laptop disk/bandwidth ke liye impractical hai.
- License CC-BY-4.0 hai — hackathon use ke liye clean, sirf attribution chahiye.
**Alternatives considered:**
- Poora dataset (180 GB) ek saath download karna — reject kiya: PRD ka apna "Risk 6: Overengineering" isi tarah ke premature scope-creep ko warn karta hai, aur cross-sensor split akela pipeline validate karne ke liye kaafi hai.
- Sirf synthetic shards se start karna — reject kiya: cross-sensor split available hone ke bawajood synthetic-only start karna scientifically weaker hota (real data ki jagah simulated degradation), jabki real data available aur chhota size mein hai.
- India-specific HR source (Cartosat/Bhuvan) dhoondhna — abhi tak koi ready-to-use paired dataset identify nahi hua hai; is decision ko open rakha gaya hai (see "Open Considerations" neeche).
**Status:** Accepted. Cross-sensor pull kiya ja raha hai (D003 dekho).

---

## D003 — Store dataset under `ml/datasets/raw/sen2naip/`
**Date:** 2026-09-08
**Decision:** Downloaded zip aur extracted files `ml/datasets/raw/sen2naip/` ke andar rakhenge, PRD ke repo-structure (`ml/datasets/`) ke mutabik.
**Reasoning:** PRD ka Section 58 repo layout already `ml/datasets/` ko dataset-related cheezon ke liye designate karta hai — koi naya convention banane ki zaroorat nahi.
**Alternatives considered:** Root-level `/data` folder (PRD Section 19 mein prototype storage ke liye suggest kiya gaya) — reject kiya kyunki woh runtime/inference storage (`input/processed/output/uncertainty/models`) ke liye hai, training dataset ke liye nahi. Training data `ml/datasets/` mein rehna zyada consistent hai ML pipeline code ke saath.
**Status:** Accepted.

---

## D004 — Adopt PRD's proposed repo structure as-is for the directory skeleton, defer heavy infra implementation
**Date:** 2026-09-08
**Decision:** PRD Section 58 ka poora directory skeleton (`frontend/`, `backend/`, `ml/`, `geospatial/`, `experiments/`, `notebooks/`, `configs/`, `tests/`, `docker/`) create kar diya gaya hai. Lekin PostGIS/Redis/Celery/S3-MinIO jaisa heavy infra, aur DINOv3 perceptual loss / ensemble-based uncertainty jaisi PRD ki "nice-to-have" choices, **abhi implement nahi ki jayengi** — sirf folder skeleton maujood hai, code nahi.
**Reasoning:** Directory layout khud lightweight hai — empty folders banane mein koi cost nahi, aur future code isi structure mein cleanly fit ho jayega. Lekin actual infra (PostGIS/Redis/Celery) aur exotic loss/uncertainty components ko abhi build karna PRD ke apne "Risk 6: Overengineering" warning ke against jaata — MVP ke liye simpler alternatives (local file storage, synchronous/simple background tasks, single-pass heteroscedastic uncertainty instead of MC ensemble) zyada hackathon-realistic hain. Yeh final nahi hai — jab team infra scaling ki zarurat mehsoos kare, tab yeh decision revisit hoga.
**Alternatives considered:** Poora backend stack (FastAPI+PostGIS+Redis+Celery) turant scaffold karna — abhi ke liye deprioritize kiya, kyunki koi backend code likhne ka explicit ask nahi tha is step mein; sirf structure banane ka tha.
**Status:** Accepted (structure only). Infra/implementation decisions open hain — dekho "Open Considerations".

---

## D005 — Git repo init: exclude raw dataset and future build artifacts via `.gitignore`
**Date:** 2026-09-08
**Decision:** Repo ko `git init` karke `https://github.com/Vijay6923/GeoSR-4.git` par push kiya. `.gitignore` mein `ml/datasets/raw/` (aur generally `*.zip`), Python/Node build artifacts, model checkpoints, `.env`, aur runtime `/data/` dir ko exclude kiya. `README.md` naya banaya (PRD/decisions.md/dataset ka pointer, repo structure overview).
**Reasoning:** `cross-sensor.zip` (2.1 GB) GitHub ki 100 MB per-file hard limit se 20x bada hai — push hoga hi nahi. Aur commit karne ki zarurat bhi nahi kyunki ek `hf_hub_download` call se reproduce ho jata hai (D002 mein documented). Build artifacts (`node_modules`, `__pycache__`, checkpoints) bhi isi tarah reproducible/generated hain, repo mein rakhna sirf bloat karega.
**Alternatives considered:** Git LFS use karke dataset ko track karna — abhi ke liye reject kiya, kyunki dataset already ek documented one-line command se re-fetchable hai; LFS ka setup overhead is stage par unnecessary hai.
**Status:** Accepted.

---

## D006 — Phase 1 close-out: verified dataset structure empirically (not just from the paper)
**Date:** 2026-09-08
**Decision:** `cross-sensor.zip` extract karke actual files inspect kiye, sirf paper ke summary par trust nahi kiya. Verified: 2,851 `ROI_*` folders, har ek mein `lr.tif` (4×121×121, int32, EPSG:32611, 10 m, nodata=-2147483648), `hr.tif` (4×484×484, uint8, 2.5 m, nodata=0), aur `metadata.json` (s2_id, s2_date, naip_id, naip_date, QA1, QA2). 626 distinct MGRS tiles mile (S2 scene id se extract kiya), jo geographic diversity confirm karta hai for a proper region-disjoint split.
**Reasoning:** PRD khud kehta hai "validation against reference data is essential" — wahi principle apne dataset assumptions par bhi apply hona chahiye. Band order (R,G,B,NIR) empirically confirm kiya pixel statistics se (band 3 ka mean sabse zyada — NIR ke liye expected, vegetation ki wajah se). Yeh Phase 1 ("Dataset v1") ka deliverable complete karta hai.
**Alternatives considered:** Paper ke documented specs par blindly trust karke seedha training code likhna — reject kiya, kyunki agar assumptions galat nikalte to baad mein training silently broken hota (wrong band order ya wrong normalization divisor jaisi cheezein debug karna mushkil hai).
**Status:** Accepted. Phase 1 complete.

---

## D007 — Phase 2: tile-disjoint train/val/test split, in-memory Dataset/DataLoader instead of pre-dumped `.npy` patches
**Date:** 2026-09-08
**Decision:** `ml/datasets/sen2naip.py` mein ek `tile_disjoint_split()` function likha jo ROIs ko unke S2 MGRS tile ke hisaab se group karke poore tile ko ek hi split (train/val/test — 80/10/10 by tile count) mein daalta hai, taaki spatially close patches alag-alag splits mein na jaayein. `SEN2NAIPCrossSensor` PyTorch `Dataset` class banayi jo `lr.tif`/`hr.tif` ko rasterio se read karke normalize karti hai (LR ÷10000 reflectance scale, HR ÷255 8-bit scale, dono [0,1] mein clip kiye).

PRD ka Phase 2 deliverable literally `preprocess.py` script tha jo `patch_001.npy` jaisi files disk par dump karta — humne iski jagah direct in-memory `Dataset`/`DataLoader` approach liya.
**Reasoning:**
- Data already pre-patched hai (121×121 / 484×484 fixed-size tiles) — is dataset ke liye separate tiling/patch-extraction step ki zaroorat nahi (woh step Phase 7+ mein relevant hoga jab hum poori Sentinel-2 scene par inference chalayenge, tab tiling zaroori hoga).
- Region-based split PRD ka explicit requirement hai (§45: "never randomly mix neighboring patches... data leakage"). MGRS tile ek natural, metadata mein already available geographic grouping hai — isse manually region-boundary draw karne ki zaroorat nahi padi.
- `.npy` mein pre-dump karna 2,851 pairs ke liye disk space double karta (rasterio read already fast hai prototyping ke liye) — is stage par unnecessary I/O overhead.
- Nodata handling: LR ke nodata pixels (-2147483648) ko 0 se replace kiya normalize karne se pehle, poore ROI ko discard nahi kiya — kyunki edge-of-tile nodata common hai aur pura pair discard karna data loss hoga. Yeh ek simplification hai; agar training mein artifacts dikhein to isko refine karna hoga (see Open Considerations).
**Alternatives considered:** Literal `preprocess.py` → `.npy` files approach — reject kiya (reasoning upar). ROI-level random split (PRD explicitly warns against) — reject kiya.
**Status:** Accepted. Smoke-tested (`ml/datasets/_smoke_test.py`) — batch load, shapes, normalization range, aur tile-disjointness sab verified working.

---

## D008 — Fixed normalization: per-band percentile scaling instead of fixed /10000, /255 divisors
**Date:** 2026-09-08
**Decision:** D007 ka normalization (LR ÷10000, HR ÷255) replace kiya per-band affine scaling se, jahan har band ka [2nd, 98th] percentile TRAIN split ke 300-ROI sample se compute kiya jaata hai (`ml/datasets/compute_stats.py` → `configs/normalization_stats.json`), phir har image ko us range ke hisaab se [0,1] mein clip+scale kiya jaata hai.
**Reasoning:** Bicubic baseline pehli baar run kiya to PSNR sirf 9.83 dB aaya — natural-image SR mein typically bicubic 25-35 dB deta hai, to yeh clearly wrong tha. Diagnosis: LR ka ÷10000 (Sentinel-2 ka theoretical saturation ceiling, jo real scenes shayad hi kabhi touch karte hain) aur HR ka ÷255 (jo already ek separate 8-bit contrast-stretch process — dataset paper confirm karta hai ki `hr.tif` = "NAIPh", NAIP ko S2 ke against histogram-matched, phir 8-bit mein re-quantized) — yeh do completely different, uncalibrated scales hain. Ek hi pair par check kiya: SR (bicubic-upsampled LR) ka std HR ke std se 15-20x chhota tha, jabki correlation moderate-positive tha (0.53-0.63) — matlab spatial alignment thik hai (koi misalignment bug nahi), sirf dono images alag dynamic range use kar rahi thi.

Fix ke baad PSNR 14.07 dB, SSIM 0.38, SAM 17.6°, ERGAS 15.87 (n=279 val pairs) aaya — better, but abhi bhi low-ish compared to typical same-sensor synthetic-degradation SR benchmarks (jahan bicubic often 25+ dB deta hai). Yeh ab genuine hai — cross-sensor real data (S2 vs NAIP, alag spectral response functions, alag viewing/illumination geometry) known-hard hai literature mein, exactly isi wajah se dataset ke authors ne "cross-sensor" (hard, real) aur "synthetic" (easier, same-sensor degradation) splits alag rakhe hain. In numbers ko as-is report kar rahe hain, PRD ke apne "never fabricate metrics" principle ke mutabik.
**Alternatives considered:** Per-image (instead of per-band-global) min-max normalization — reject kiya, kyunki woh scene-to-scene genuine brightness differences ko erase kar deta (jo physically meaningful hai reflectance data ke liye, PRD ke "preserve spectral consistency" requirement ke against jaata). Fixed constants continue karna — reject kiya after diagnosis confirm hua ki woh scientifically invalid comparison de raha tha.
**Status:** Accepted. Real baseline numbers ab pipeline-verified hain, fabricated nahi.

---

## D009 — EDSR baseline: fixed a dead-gradient bug (clamp() inside the training forward pass)
**Date:** 2026-09-08
**Decision:** `EDSR.forward()` se `torch.clamp(output, 0, 1)` hata diya. Model ab raw (unbounded) output deta hai training ke waqt; clamping sirf inference/evaluation wrapper mein apply hoti hai (`train_edsr.py`'s `evaluate()`), final pixel values banane ke liye — model ke andar nahi.
**Reasoning:** 16-block/64-channel EDSR banane se pehle 4-block/16-channel tiny version par overfit sanity check kiya (2 hi training examples par, standard ML debugging practice — agar chhote se model sirf 2 examples bhi overfit nahi kar sakta to pipeline mein zaroor bug hai). Loss 15 epochs (30 steps) tak bilkul flat raha, jo suspicious tha. Gradient norm directly check kiya to woh exactly 0.0 tha step ~50 ke baad — matlab gradient completely mar chuka tha.

Root cause: model ka raw output init ke time already [-0.24, 0.25] range mein tha (kuch pixels 0 se neeche), aur `torch.clamp()` zero-gradient hota hai apni clip range ke bahar. Jaise-jaise training aage badhti, aur zyada pixels [0,1] range ke bahar drift karte gaye (L1 loss ka gradient push karta hai), aur end mein saare outputs saturate ho gaye — ek "dead ReLU"-jaisa trap, lekin poore output tensor ke liye.

Fix ke baad same 2-example overfit test: loss 0.60 → ~0.10 (150 steps mein), gradient norm poore time healthy raha (kabhi 0 nahi hua).
**Alternatives considered:** `sigmoid()` output activation (jo hamesha non-zero gradient deta hai, though extremes par vanishing) — reject kiya kyunki simple linear output + external clamp zyada standard practice hai SR literature mein, aur training ko unnecessarily constrain nahi karta.
**Status:** Accepted. Yeh bug agar catch nahi hota, to Colab/Kaggle par poora real training run silently fail hota (loss kabhi decrease nahi hota) — kaafi compute aur time waste hota debugging mein baad mein.

---

## D010 — Split dev workflow: write/smoke-test code locally (CPU), run real training on Colab (GPU)
**Date:** 2026-09-08
**Decision:** Model/training code is written and validated locally on tiny subsets (few ROIs, few steps, small model config) purely to catch bugs. Actual full training runs (all train-split ROIs, full-size EDSR: 16 blocks/64 channels, many epochs) happen on Colab GPU, via `notebooks/train_edsr_colab.ipynb`, which clones the pushed repo, re-downloads only the cross-sensor split, and reuses the committed `configs/normalization_stats.json` (does not recompute it — must stay identical across local dev and Colab runs).
**Reasoning:** Laptop has no CUDA GPU; a full 2,283-pair EDSR training run would be impractically slow on CPU. But local smoke-testing on tiny subsets before touching Colab compute is what caught the D009 dead-gradient bug in the first place — if that bug had only surfaced on a full Colab GPU run, it would've wasted real Colab compute-time/quota debugging something a 2-example, 30-second local test could catch.
**Alternatives considered:** Train fully on this laptop regardless of speed — rejected by user, given (a) time cost and (b) this exact local-smoke-test-first workflow already proved its value by catching D009.
**Status:** Accepted.

---

## D011 — First real model-vs-baseline comparison: EDSR beats Bicubic on 3/4 metrics
**Date:** 2026-09-08
**Decision:** EDSR-baseline (16 blocks/64 channels) ko 20 epochs, full train split (2,283 pairs), Colab T4 GPU par train kiya. Full validation split (279 pairs, same protocol jo bicubic baseline ke liye use hua) par evaluate kiya `ml/evaluation/evaluate_checkpoint.py` se.

**Result (n=279, dono same val set par):**

| Metric | Bicubic | EDSR (epoch 19) | Change |
|---|---|---|---|
| PSNR | 14.07 dB | 16.77 dB | +2.70 dB |
| SSIM | 0.385 | 0.443 | +0.058 |
| SAM | 17.64° | 11.41° | -6.23° |
| ERGAS | 15.87 | 15.57 | ~flat |

**Reasoning:** Training ke dauraan per-epoch eval sirf 50 val samples par tha (speed ke liye) — usse directly bicubic (jo poore 279 pairs par tha) se compare karna unfair hota. Isliye final checkpoint ko poore val split par phir se evaluate kiya, taaki comparison genuinely apples-to-apples ho.

PSNR/SSIM/SAM teeno decisively improve hue — yeh evidence hai ki learned model naive interpolation se better hai is cross-sensor task par bhi (jahan D008 mein dekha ki even bicubic ka baseline khud modest tha domain-gap ki wajah se). ERGAS flat raha — aur uska std (55.16) uske apne mean (15.57) se bahut zyada hai, jo suggest karta hai ki kuch outlier patches (shayad low-mean reference band wale, jahan ERGAS ka per-band RMSE/mean ratio explode karta hai) poore average ko skew kar rahe hain, na ki ERGAS genuinely uninformative hai.
**Alternatives considered:** Sirf training ke dauraan ke 50-sample numbers ko final result maan lena — reject kiya, kyunki woh statistically kam reliable hai aur bicubic ke saath unfair comparison hota.
**Status:** Accepted. Phase 3 (EDSR baseline) ka core result mil gaya. ERGAS outlier investigation Open Considerations mein add kiya.

---

## D012 — Phase 4: SwinIR architecture choices (window_size=11, lightweight config)
**Date:** 2026-09-08
**Decision:** SwinIR implement kiya (`ml/models/swinir/swinir.py`) window-based self-attention ke saath — window_size=11, embed_dim=60, 4 RSTB blocks (har ek depth-2), 6 attention heads. Same L1-only, local-CPU-smoke-test → Colab-GPU-train workflow (D010) jo EDSR ke liye use hua.
**Reasoning:**
- window_size=11 specifically isliye chuna kyunki 121 (hamare LR patch ka height/width) = 11×11 exactly — is se koi input padding nahi chahiye. Yeh dataset-specific choice hai; agar future mein arbitrary-size Sentinel-2 scenes par tiled inference chalayenge (Phase 7), tab tile size ko window_size ka multiple rakhna hoga ya padding logic add karni hogi.
- embed_dim=60 / depths=(2,2,2,2) / heads=6 ek "SwinIR-light" scale hai (original paper ke full-size model se chhota) — hackathon compute budget (Colab T4) ke hisaab se reasonable starting point, EDSR (16 blocks/64 channels, ~1.5M params) se roughly comparable capacity range mein.
- EDSR ke D009 bug (training-time clamp gradient-kill) se seekh kar, is baar model likhne se pehle hi forward pass shape-check aur phir 2-example overfit sanity check kiya (before kisi bhi Colab compute use karne ke) — loss 0.58→0.11 (60 steps), gradient norm poore time healthy raha. Isse confirm hua ki window partition/reverse, shifted-window masking, relative position bias, aur RSTB residual connections sab sahi wire hue hain.
- `evaluate_checkpoint.py` ko generalize kiya `--model-type` flag ke saath (edsr/swinir dono), taaki fair full-val-set comparison ek hi script se ho sake, code duplicate na ho.
**Alternatives considered:** Full-size SwinIR (jaisa original paper mein, ~11M+ params, deeper RSTBs) — abhi ke liye reject kiya, PRD ke "Risk 6: Overengineering" ke mutabik; agar lightweight version promising results deta hai to scale up karna easy hoga.
**Status:** Accepted. Local smoke test pass. Colab GPU training run pending (user action).

---

## D013 — SwinIR trained: roughly matches EDSR at less than half the parameters
**Date:** 2026-09-08
**Decision:** SwinIR (embed_dim=60, depths 2,2,2,2, heads=6) ko 20 epochs, full train split, Colab T4 par train kiya. Full val split (279 pairs) par evaluate kiya.

**Three-way comparison (n=279, sab same val set, same protocol):**

| Metric | Bicubic | EDSR (1.52M params) | SwinIR (0.68M params) |
|---|---|---|---|
| PSNR | 14.07 dB | 16.77 dB | 16.92 dB |
| SSIM | 0.385 | 0.443 | 0.429 |
| SAM | 17.64° | 11.41° | 11.60° |
| ERGAS | 15.87 | 15.57 | 14.56 |

**Reasoning:** Dono learned models bicubic ko clearly beat karte hain (PRD ka expected core result). EDSR aur SwinIR ke beech PSNR/SAM lagbhag tied hain, SSIM mein EDSR thoda aage, ERGAS mein SwinIR thoda aage — koi decisive winner nahi hai raw metrics mein.

Lekin: SwinIR ke paas EDSR se **2.2x kam parameters** hain (683K vs 1.52M) — phir bhi comparable quality de raha hai. Yeh PRD ke Section 29 ("why transformer") ke claim ko support karta hai (long-range spatial relationships ko better capture karta hai, isliye kam capacity mein bhi competitive result), lekin isko "transformer clearly better hai" jaisa overclaim nahi kar rahe — is stage par honest finding yeh hai ki **parameter-efficiency mein SwinIR aage hai, absolute quality mein abhi tied hai**. Agar SwinIR ko EDSR jitni hi capacity di jaaye (bigger embed_dim/deeper RSTBs), woh potentially aage nikal sakta hai — yeh Open Considerations mein track kiya gaya hai.

Numbers fabricate nahi kiye — jo mila wahi report kiya, chahe woh "transformer clearly wins" wali clean story na ho.
**Alternatives considered:** Sirf absolute metrics dekh kar "SwinIR EDSR se better nahi hai" keh dena — reject kiya, kyunki parameter-count context ke bina yeh comparison incomplete/misleading hota.
**Status:** Accepted. Phase 4 (SwinIR baseline) complete.

---

## D014 — Phase 5: spectral + edge loss added (ablation on top of EDSR, not a new architecture)
**Date:** 2026-09-08
**Decision:** `ml/losses/spectral.py` (differentiable SAM, torch-native version of the eval metric) aur `ml/losses/edge.py` (Sobel-gradient L1 loss) add kiye. `train_edsr.py` aur `train_swinir.py` dono mein `--lambda-spectral`/`--lambda-edge` CLI flags add kiye (default 0.0 = pure L1, matlab existing baseline runs ka behavior bilkul same rehta hai, backward compatible). Ablation architecture change nahi hai — EDSR ka wahi 16-block/64-channel config reuse kiya, sirf loss function change kiya, taaki loss ka effect architecture se isolate ho sake (PRD Section 32: Model A vs Model A + spectral loss).
**Reasoning:** SAM loss ke liye `acos()` use kiya (differentiable spectral angle) — `acos` ka gradient ±1 ke paas explode karta hai, isliye cosine value ko `[-1+1e-7, 1-1e-7]` mein clamp kiya, jo `compute_sam` (eval metric) ke `[-1,1]` clamp se thoda tighter hai specifically gradient stability ke liye. Edge loss Sobel filter se gradient magnitude nikal ke dono images (SR, HR) ke beech L1 leta hai.

λ_spectral aur λ_edge dono ke default 0.1 rakhe pehle ablation run ke liye — yeh ek starting guess hai, properly tuned nahi (hyperparameter search is stage par scope se bahar hai, PRD ke anti-overengineering ethos ke mutabik). 2-example overfit sanity check (D009/D012 jaisa pattern) pehle chalaya combined loss ke saath — loss 0.76→0.16 (60 steps), gradient norm healthy raha, koi NaN/explosion nahi.
**Alternatives considered:** Naya model architecture banana loss ke saath — reject kiya, kyunki tab yeh confound ho jaata ki improvement architecture se aaya ya loss se. Perceptual/DINOv3 loss abhi add nahi kiya — woh already Open Considerations mein "stretch goal" hai, aur is ablation ko simple rakhna hai pehle.
**Status:** Accepted. Local smoke-tested (dono scripts, combined loss). Colab ablation run pending (user action) — `notebooks/train_edsr_colab.ipynb` mein naya "Phase 5 ablation" section add kiya jo same EDSR config ko spectral+edge loss ke saath train karke turant full-val-set evaluate bhi kar deta hai.

---

## D015 — ERGAS outlier diagnosed: near-zero-reflectance band, not a bug; now reporting median too
**Date:** 2026-09-08
**Decision:** Investigate kiya ki bicubic baseline ke ERGAS ka std (55.16) itna zyada kyun tha apne mean (15.57) se. Poore val split (279 pairs) par per-patch ERGAS sort karke dekha: `ROI_05939` = 771.5 (baaki sab 2.5-58 range mein, median 11.66). Us patch ke HR band means dekhe: band index 2 ka mean sirf 0.0075 tha (0-1 normalized scale par, matlab bahut low reflectance — likely water body ya shadow). ERGAS formula `100 * ratio * sqrt(mean((RMSE_band/mean_band)²))` hai — near-zero mean_band ek modest RMSE ko bhi drastically amplify kar deta hai us band ke liye, aur woh akela poore patch ke ERGAS ko dominate kar deta hai.

Fix: `run_baseline.py` aur `evaluate_checkpoint.py` dono ab median bhi print karte hain ERGAS ke liye (mean ke saath), kyunki mean is known ERGAS limitation ke against robust nahi hai.
**Reasoning:** Yeh ek documented, well-known ERGAS weakness hai remote-sensing literature mein (low-reflectance regions, especially water, denominator explode karte hain) — code mein koi bug nahi tha. Median report karna standard practice hai isi wajah se. Single outlier ka contribution itna bada hai ki woh akela poore 279-sample std ko explain kar deta hai — baaki distribution genuinely well-behaved hai.
**Alternatives considered:** Us specific ROI ko dataset se exclude/filter karna — abhi ke liye reject kiya, kyunki woh genuine real data hai (dataset ka hissa hona chahiye), sirf reporting robust honi chahiye, data cherry-pick nahi karna.
**Status:** Accepted. Open Consideration resolved.

---

## D016 — Phase 6: single-pass heteroscedastic uncertainty (not MC-ensemble), with a real gradient-explosion bug caught in smoke testing
**Date:** 2026-09-08
**Decision:** Uncertainty estimation ke liye single-pass heteroscedastic head implement kiya (`ml/uncertainty/heteroscedastic.py`) — EDSR ko `out_channels=8` diya (4 mean + 4 log-variance), Gaussian NLL loss (`nn.GaussianNLLLoss`) se train kiya. PRD ka suggested MC-ensemble (5x forward pass, multiple models) use nahi kiya.
**Reasoning:** MC-ensemble ek forward pass ki jagah 5x compute maangta — Colab T4 (free tier) ke limited GPU-hours budget mein yeh costly hai, especially jab hume already EDSR/SwinIR/ablation ke liye multiple 20-epoch runs chahiye. Single-pass heteroscedastic head ek hi forward pass mein SR image + confidence map dono deta hai.

**Real bug caught during smoke testing**: Jab main pehle 2-example overfit test kiya lr=1e-2 (jo EDSR/SwinIR ke liye kaam kiya tha) par, training completely diverge ho gayi — loss aur gradient norm dono lakhon tak explode ho gaye (grad_norm 1e8+ tak), reconstruction error 160,000+ tak. Yeh Gaussian NLL loss ka known instability hai (Kendall & Gal, 2017): model predicted variance ko error se zyada fast shrink kar sakta hai, jisse `(error)²/variance` term explode karta hai, jo phir poore model (mean prediction sahit) ko destabilize kar deta hai — plain L1 loss jaisa forgiving nahi hai.

Diagnosis: script ka actual default lr=1e-4 par retest kiya (1e-2 sirf meri quick-debug choice thi, production default nahi) — training stable nikli (loss 0.14→-1.48 smoothly, grad_norm bounded 0.36-7.5, recon error 0.50→0.12). Toh yeh fundamentally broken nahi tha, lekin itni violently diverge hone ki capability dekh kar, defensive measure zaroori laga: `torch.nn.utils.clip_grad_norm_(max_norm=5.0)` add kiya training loop mein, taaki full-scale Colab run mein koi ek bad batch bhi poori training session waste na kare.
**Alternatives considered:** MC-ensemble (PRD ka suggestion) — reject kiya, compute cost ki wajah se (upar reasoning). Warm-start karna (pehle plain-L1 model train karke, phir uncertainty head ke liye fine-tune karna, jo standard practice hai NLL instability avoid karne ke liye) — abhi ke liye add nahi kiya kyunki lr=1e-4 par already stable tha; agar Colab par full-scale run mein bhi instability dikhe to yeh next fix hoga.
**Status:** Accepted. Local smoke-tested (shape check + overfit sanity check + full script run). Colab GPU run pending (user action).

---

## D017 — Phase 7: tiled inference with Hann-blending + GeoTIFF export, verified end-to-end
**Date:** 2026-09-08
**Decision:** `geospatial/tiling/tiler.py` (overlapping-tile extraction + Hann-window blended reassembly, PRD section 25-26), `geospatial/geotiff/export.py` (CRS/transform-preserving GeoTIFF writer, PRD section 40-41), aur `ml/inference/infer_scene.py` (poora pipeline: tile → normalize → infer → blend → denormalize → write) banaye. Abhi sirf EDSR support karta hai (SwinIR ko window_size-multiple tile size chahiye, D012 — abhi handle nahi kiya).
**Reasoning:** Trained model sirf apne training patch size (121×121) par kaam janta hai, lekin real Sentinel-2 scenes bahut bada hote hain — isliye tiling zaroori hai. Bina overlap-blending ke, tile boundaries par visible seams aa sakte hain (PRD Section 26 ka concern).

Verification (sirf "code likha, ho gaya" nahi bola):
1. **Tiler correctness**: Ek synthetic scene par identity-transform (scale_factor=1) test kiya — extract_tiles + blend_tiles round-trip karke original ko wapas reconstruct kar paya, max error 2.4e-7 (float32 precision noise ke barabar). Isse confirm hua ki Hann-window blending aur indexing sahi hai.
2. **End-to-end pipeline**: Ek real `lr.tif` (121×121) par chalaya (deliberately chhota `--tile-size 64` use kiya taaki multi-tile blending path genuinely exercise ho, na ki trivial single-tile case) — 9 tiles bane, sahi se blend hue, output GeoTIFF (484×484) mila.
3. **Geospatial preservation check**: Output GeoTIFF ka CRS (EPSG:32611), origin, aur bounds input ke exactly same the — sirf resolution 10m→2.5m (4x) aur pixel dimensions 121→484 (4x) sahi se scale hue. Yeh directly verify karta hai PRD ka core Phase 7 requirement, sirf assume nahi kiya.
4. Output pixel values (42-93 range) denormalized HR-domain scale mein the (D008's `denormalize()` function use kiya) — [0,1] normalized junk nahi.
**Alternatives considered:** Naive non-overlapping tiling (bina blending ke) — reject kiya, PRD explicitly warns against visible tile-boundary artifacts. SwinIR ke liye bhi is turn mein support add karna — abhi ke liye defer kiya (window_size padding logic extra kaam hai, EDSR se pipeline validate karna pehle zaroori tha).
**Status:** Accepted. Phase 7 core pipeline verified working.

---

## D018 — infer_scene.py extended: SwinIR tiling + uncertainty dual-GeoTIFF output
**Date:** 2026-09-08
**Decision:** `ml/inference/infer_scene.py` ko generalize kiya — `--model-type` (edsr/swinir) aur `--uncertainty` flag add kiye. SwinIR ke liye tile_size ko window_size ka multiple hona chahiye (validate kiya, error deta hai agar nahi hai) — koi extra padding logic nahi chahiye thi kyunki `extract_tiles` already edge-padding kar deta hai poore scene ko tile_size ka multiple banane ke liye (D017 mein already implement tha). Uncertainty checkpoint ke liye mean aur log_var ko alag-alag blend kiya (`blend_tiles` dono baar call kiya), phir std ko `std_norm * (hi-lo)` se physical scale mein convert kiya (linear affine denormalization ke under, `Var(aX)=a²Var(X)` isliye `std(aX)=a·std(X)` — mathematically valid), aur ek dusra GeoTIFF likha uncertainty map ke liye.
**Reasoning:** Dono naye code paths (`--model-type swinir`, `--uncertainty`) smoke test kiye tiny checkpoints se (jo phase 4/6 ke smoke tests se bache the). SwinIR path clean chala (16 tiles, 44x44, window_size=11 ka multiple). Uncertainty path bhi chala, dono GeoTIFF likhe gaye — lekin std values (104-168) bahut large the HR range (~42-200) ke against. Yeh check kiya aur confirm kiya ki yeh expected hai: checkpoint sirf 4 gradient steps trained tha (D016 ka smoke test), untrained network mein log_var≈0 hota hai (near-zero init), matlab var≈1, std≈1 in normalized [0,1] space — jo physical scale mein convert hone ke baad genuinely bahut bada dikhega. Yeh code bug nahi hai, balki mathematically expected behavior hai ek barely-trained model ke liye. Real calibration quality sirf Colab ke actual-trained uncertainty checkpoint se judge ho sakti hai.
**Alternatives considered:** Dono model types ke liye alag-alag script rakhna (jaisa training scripts mein hai) — reject kiya kyunki inference orchestration logic (tile→infer→blend→denormalize→write) same hai dono ke liye, sirf model construction alag hai — is level ka parameterization (jaisa `evaluate_checkpoint.py` mein already hai) DRY rakhta hai bina overengineer kiye.
**Status:** Accepted. Dono open items (SwinIR tiling, uncertainty GeoTIFF) close ho gaye.

---

## D019 — Phase 5 ablation result: spectral+edge loss (λ=0.1/0.1) did NOT help, slightly hurt
**Date:** 2026-09-08
**Decision:** Colab run complete hua. Full-val-set (n=279) comparison:

| Metric | Plain EDSR (D011) | EDSR + spectral(0.1) + edge(0.1) | Change |
|---|---|---|---|
| PSNR | 16.77 dB | 16.45 dB | -0.32 dB |
| SSIM | 0.4427 | 0.4364 | -0.0063 |
| SAM | 11.41° | 11.90° | +0.49° (worse) |
| ERGAS | 15.57 | 15.60 | +0.03 (~flat, dono ke std bahut high hain outlier ki wajah se D015) |

Sab 4 metrics mein slight regression, koi improvement nahi. Numbers as-is report kar rahe hain, chahe woh "loss addition helped" wali expected story na ho.
**Reasoning:** λ=0.1/0.1 sirf ek starting guess tha (D014 mein hi flag kiya gaya tha ki tuning baaki hai). Auxiliary loss terms (spectral, edge) primary reconstruction objective (L1) ke saath compete kar sakte hain agar weight zyada ho — model thoda trade-off kar raha hoga spectral-angle/edge-sharpness ke liye reconstruction accuracy ki keemat par. Yeh ek genuine, honest negative result hai is λ setting ke liye — iska matlab yeh nahi ki spectral/edge loss concept hi galat hai, sirf itna hai ki 0.1/0.1 weight is architecture/task ke liye kaam nahi kiya.

Note: is Colab run mein `evaluate_checkpoint.py` ka purana version chal raha tha (session D015 ke push se pehle clone hua tha) — isliye ERGAS ka median print nahi hua, sirf mean/std. Agli baar isi session mein kaam continue karna ho to `git pull` chalana zaroori hai naye fixes lene ke liye.
**Alternatives considered:** Result ko chhupana ya "roughly same hai" bol ke downplay karna — reject kiya, PRD ka explicit "never fabricate/spin metrics" principle. λ ko turant retune karna — abhi ke liye hold kiya kyunki user ka immediate priority local demo hai; λ sweep Open Considerations mein already tracked hai.
**Status:** Accepted. Phase 5 result recorded (negative finding, still valuable — batata hai λ tuning zaroori hai before spectral/edge loss ko production config maanne se pehle).

---

## D020 — First local end-to-end demo: SwinIR chosen over EDSR (visibly better despite tied metrics)
**Date:** 2026-09-08
**Decision:** Real trained checkpoints (`experiments/edsr/edsr_epoch19.pt`, `experiments/swinir/swinir_epoch19.pt`, dono Colab se download kiye) ko local machine par `infer_scene.py` se run kiya, ek held-out validation patch (`ROI_0045`, training mein kabhi nahi dikha) par, `visualize_demo.py` se side-by-side comparison banaya (LR input | SR output | ground truth NAIP).

Dono model ka output visually inspect kiya: **EDSR** ka output ek strong diagonal ripple/moiré texture artifact dikhata hai poore image mein, jo ground truth mein bilkul nahi hai. **SwinIR** ka output isse kaafi behtar hai — colors ground truth se match karte hain (asli green canopy, EDSR ke grey-purple wash ke against), overall structure/shapes sahi hain, aur artifact bhi present hai lekin bahut halka (light checkerboard-jaisa texture, severe ripple nahi).

Isliye demo ke liye **SwinIR checkpoint use kiya**, EDSR nahi — chahe D013 mein dono roughly metric-tied the (PSNR/SAM), visual quality mein clear difference hai. Yeh important insight hai: **raw PSNR/SSIM tie hone ka matlab equal perceptual quality nahi hai**.
**Reasoning:** Artifact ka likely cause: PixelShuffle-based sub-pixel convolution upsampling (dono EDSR aur SwinIR isi `UpsampleBlock` class ko reuse karte hain) — yeh well-documented checkerboard/ripple artifact produce karta hai jab tak pre-shuffle conv layer ko specifically initialize na kiya jaaye (ICNR initialization, ya post-shuffle blur layer add karke). Abhi humne yeh nahi kiya — standard random init use kiya.
**Alternatives considered:** Artifact ko fix karne ki koshish karna abhi hi (ICNR init add karna, retrain karna) — reject kiya for now, kyunki user ka immediate priority "aaj demo dikhana" tha, aur SwinIR ka output already demo-presentable hai. ICNR fix Open Considerations mein track kiya gaya hai future refinement ke liye.
**Status:** Accepted. Local demo working end-to-end: real Sentinel-2-scale input → real <4m (2.5m) SR output, geospatially correct, visually reasonable. Saved to `experiments/demo/` (gitignored, local only).

---

## D021 — Backend: synchronous FastAPI MVP, one endpoint, no job queue/DB
**Date:** 2026-09-08
**Decision:** `backend/app/main.py` — ek hi endpoint `POST /api/infer`: GeoTIFF upload karo, response mein hi SR GeoTIFF + before/after PNG previews (base64) wapas milte hain. Model (SwinIR, D020 ke checkpoint) startup par ek baar load hota hai, har request par nahi. No Redis/Celery/job-queue, no PostgreSQL/PostGIS — sab kuch ek request-response cycle mein, in-memory (rasterio `MemoryFile` use kiya, disk par temp files bhi nahi likhi).

Reusability ke liye `infer_scene.py` ko refactor kiya: tiling/blending/inference logic ab `run_sr_inference()` function mein hai (model + numpy array leta hai), jise CLI script aur backend dono use karte hain — duplicate nahi kiya. Refactor ke baad regression-test kiya (same input → exact same output, max diff 0.0 pre-refactor CLI output ke against).
**Reasoning:** User ne explicitly synchronous mode choose kiya (job-queue PRD ka full vision hai, lekin bade scenes ke liye zaroori hai; humara demo-size patch input ke liye ek request 1.09 second mein complete ho jata hai — async/polling ki zaroorat nahi abhi). Yeh D004 ke decision se bhi consistent hai (heavy infra MVP ke liye defer karna).
**Verification**: sirf "code likh diya" nahi — actual server start karke real GeoTIFF upload kiya curl se, response verify kiya (shapes, resolution, PNG/GeoTIFF decode karke dekha ki corrupt nahi hain, GeoTIFF ka CRS/resolution round-trip ke baad bhi sahi tha).
**Alternatives considered:** Async job-queue (Celery+Redis) abhi implement karna — reject kiya (user's explicit choice), PRD ka full vision hai lekin abhi ke MVP scope se bahar. Disk par intermediate files likhna — reject kiya, in-memory processing (MemoryFile) simpler hai aur is chhoti scale par koi disadvantage nahi.
**Status:** Accepted. Backend working end-to-end, verified with real upload.

---

## D022 — Frontend: Vite + React + TypeScript + Tailwind, single page, verified end-to-end through the dev-server proxy
**Date:** 2026-09-08
**Decision:** `frontend/` mein Vite scaffold kiya (react-ts template), Tailwind v4 (`@tailwindcss/vite` plugin — v4 mein `tailwind.config.js`/PostCSS setup ki jagah yeh recommended approach hai, purana v3-style setup nahi use kiya). Ek hi page (`App.tsx`): file upload input → `POST /api/infer` → before/after image side-by-side + GeoTIFF download button. Vite dev server ka `/api` proxy backend (port 8000) ko forward karta hai, taaki dev mein CORS ka jhanjhat na ho.
**Reasoning:** User ne explicitly single-page minimal choose kiya (multi-page PRD dashboard baad mein). Stack (React+TS+Tailwind) already PRD/README mein decided tha — koi naya decision nahi, sirf implementation.
**Verification**: Sirf `npm run build` (TypeScript compile check) hi nahi — dev server actually start kiya, `curl` se `/api/health` proxy ke through hit kiya (confirm kiya ki proxy sahi backend tak pahuchta hai), phir ek real GeoTIFF **proxy ke through** upload kiya (exactly wahi path jo browser ka `fetch()` use karega) — poora chain (Vite dev server → proxy → FastAPI → model → response) end-to-end verify hua, sirf backend ko directly test karke nahi.
**Alternatives considered:** Multi-page dashboard abhi banana — reject kiya (user's explicit choice, PRD ka full vision baad ke liye hai).
**Status:** Accepted. Full stack (backend D021 + frontend D022) working locally, browser mein use karne ke liye ready.

---

## D023 — Quality push for the demo: VGG perceptual loss + ICNR upsample fix, bundled together
**Date:** 2026-09-08
**Decision:** User ne dekha ki demo output ka visual improvement subtle tha, aur explicitly kaha "evaluator ko clearly change dikhna chahiye." Do changes ek saath kiye (normally alag-alag ablation test karte, lekin time-constraint ki wajah se bundle kiya, honestly yahan note kar raha hun):

1. **VGG perceptual loss** (`ml/losses/perceptual.py`) — pretrained VGG16 (ImageNet) ke relu3_3-tak features se SR aur HR compare karte hain (sirf RGB bands, NIR drop kiya — PRD Section 36 ka apna hint follow kiya). L1/pixel loss known-blur produce karta hai (SRGAN/ESRGAN literature se well-established) kyunki woh statistically "average plausible output" reward karta hai; perceptual loss high-level features match karke sharper/zyada realistic-looking output push karta hai.
2. **ICNR weight initialization** (`ml/models/upsample.py`) — dono EDSR aur SwinIR ka duplicate `UpsampleBlock` class ek shared module mein refactor kiya, aur usme ICNR init add kiya, jo D020 ke checkerboard/ripple artifact ko fix karta hai (PixelShuffle ke pre-shuffle conv weights ko is tarah initialize karta hai ki sab r² sub-pixel positions same kernel se start hon, matlab init ke time upsample nearest-neighbor jaisa clean ho, random-per-position nahi).

**Verification** (dono changes ke liye):
- ICNR: pehle test kiya without bias-fix — FAIL hua (2x2 output patch uniform nahi tha, std=0.084). Root cause dhoonda: `nn.Conv2d` ka default bias independently random hota hai per-channel, sirf weight equalize karna kaafi nahi tha. Bias bhi equalize kiya, phir verify kiya — ab poori tarah uniform (std=0.0 exactly, sab channels/patches mein).
- ICNR + refactor ke baad EDSR/SwinIR dono ka overfit sanity check phir se chalaya (D009/D012 jaisa) — pehle EDSR ka 60-step short test noisy dikha (lag raha tha regression hai), lekin full 150-step test (jo exact D009 protocol match karta hai) confirm kiya ki convergence healthy hai (final loss 0.102, D009 ke original 0.101 ke barabar) — short test sirf normal early-training noise pakड़ raha tha, real regression nahi tha.
- Perceptual loss: local overfit test (30 steps, combined L1+perceptual) — loss 0.55→0.20, gradient norm 11→1.8 (shrinking, healthy), koi NaN/explosion nahi. Full training script bhi smoke-test kiya end-to-end.
- SSL cert issue mila VGG16 download karte waqt (macOS python.org install ka known issue, certifi bundle use nahi ho raha tha by default) — `SSL_CERT_FILE` env var se fix kiya. Colab par yeh issue nahi aayega (proper certs already hain).

**Reasoning:** λ_perceptual=0.01 sirf ek starting guess hai (D014/D019 jaisa pattern — untuned, tuning baad mein). SwinIR ko target model banaya (D020 ke mutabik, demo ke liye already chosen).
**Alternatives considered:** Har change ko alag Colab run mein isolate karke test karna (proper ablation discipline) — reject kiya time-constraint ki wajah se; user ka immediate need ek visibly-better demo tha, do separate ~40-min Colab runs ki jagah ek run mein dono improvements bundle karna zyada practical tha. Yeh trade-off explicitly yahan document kar raha hun taaki baad mein pata rahe ki in do changes ka individual contribution isolate nahi kiya gaya.
**Status:** Accepted, local verification complete. Colab training run pending (user action).

---

## D024 — Fixed CUDA OOM in VGG perceptual loss: resize to 224x224 before feature extraction
**Date:** 2026-09-08
**Decision:** Colab par D023 ka "quality run" (SwinIR + perceptual loss) chalaya to CUDA OOM crash hua step 0 par hi — T4 (14.56 GiB) already 14.49 GiB use kar raha tha (SwinIR + optimizer + batch_size=16 @ 484×484), aur VGG ka dual forward pass (pred with grad + target no_grad, dono 484×484×16-batch par) 458 MB aur maang raha tha jo available nahi tha. Fix: `VGGPerceptualLoss._prepare()` mein ab RGB images ko VGG feed karne se pehle 224×224 (VGG ka apna native ImageNet training resolution) tak `F.interpolate` (bilinear) se resize kar dete hain.
**Reasoning:** 484×484 vs 224×224 = ~4.67x kam pixels — VGG ki poori conv stack mein activation memory proportionally kam ho jaata hai, jo is OOM (sirf 458MB short tha) ko comfortably cover karta hai. Bonus: VGG ke features actually 224px scale par hi trained/meaningful the — 484px par unbounded resolution feed karna already ek extra scale-mismatch tha (RGB-domain mismatch ke upar), to yeh fix sirf memory issue nahi, conceptually bhi zyada correct hai.
**Verification**: Local CPU test (GPU nahi hai yahan, lekin shape/gradient-flow correctness check kiya) — combined L1+perceptual loss 20 steps chalaya, loss 1.15→0.29 decrease hua, gradient norm healthy (16.1→7.7, koi explosion nahi). Actual OOM-resolution sirf Colab GPU par verify ho sakta hai (memory ka exact accounting local CPU run mein nahi dikhta) — agla Colab run isko confirm karega.
**Alternatives considered:** Batch size kam karna (16→8) instead of/along with resize — abhi ke liye sirf resize kiya (bada margin deta hai, ~4.67x), batch size same rakha taaki baseline SwinIR run (D013) ke saath directly comparable rahe (sirf loss function change ho, batch size nahi). Agar yeh bhi OOM de, batch size reduction next fallback hai.
**Status:** Accepted, locally verified. Colab retry pending (user action) — koi checkpoint pehle attempt se bacha nahi (crash step 0 par hi hua tha), poora training run phir se chalana hoga.

---

## D025 — Second OOM (different cause): CUDA allocator fragmentation, not raw capacity
**Date:** 2026-09-08
**Decision:** D024 ka resize fix kaam kiya (epoch 0 successfully complete hua, checkpoint bhi save hua) — lekin epoch 1 shuru hote hi phir OOM aaya, is baar SwinIR ke apne upsample/PixelShuffle step mein, VGG mein nahi. Error message mein clue tha: "2.08 GiB is reserved by PyTorch but unallocated" — yeh capacity issue nahi, **fragmentation** hai (total free+reserved memory kaafi thi, lekin ek single 858MB contiguous block available nahi tha). Crash specifically ek pura epoch + validation (train batch=16 → eval batch=1 → wapas train) cycle ke baad hua, jo is fragmentation-hypothesis ko support karta hai (batch size baar-baar switch karna allocator ko fragment karta hai).

Teen fixes ek saath kiye:
1. Har epoch ke end mein (checkpoint save se pehle) `torch.cuda.empty_cache()` call kiya — teeno training scripts mein (`train_swinir.py`, `train_edsr.py`, `train_edsr_uncertainty.py`, consistency ke liye, chahe abhi sirf SwinIR crash hua ho).
2. `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` env var set kiya Colab cell mein — yeh khud PyTorch ke apne error message ka suggestion hai, allocator ko existing segments expand karne deta hai naye contiguous blocks maangne ki jagah.
3. Batch size 16→8 kam kiya is specific run ke liye (extra safety margin, do OOM ke baad).
**Reasoning:** Do alag-alag OOM causes (D024: raw capacity/resolution, D025: fragmentation) ek hi "quality run" mein mile — dono fix karna zaroori tha taaki teesri baar phir se fail na ho. `torch.cuda.is_available()` guard ke saath likha taaki local CPU testing break na ho.
**Verification**: Local smoke test (CPU, `torch.cuda.is_available()` False hone ki wajah se `empty_cache()` skip hota hai) — 2 epochs clean chale, koi syntax/logic error nahi. Actual fragmentation-fix ka real verification sirf Colab GPU par hoga (memory allocator behavior local CPU run mein reproduce nahi hota).
**Alternatives considered:** Sirf batch size kam karna (bina fragmentation fix ke) — reject kiya kyunki root cause specifically fragmentation tha (capacity nahi), to sirf batch-size-reduction band-aid hota; asal fix (empty_cache + expandable_segments) zyada targeted hai.
**Status:** Accepted, locally verified (syntax/logic only). Colab retry #2 pending (user action).

---

## D026 — Before/after slider (PRD section 12), native range input instead of a drag library
**Date:** 2026-09-08
**Decision:** `frontend/src/components/BeforeAfterSlider.tsx` — static side-by-side grid ki jagah ab ek draggable before/after slider hai. Implementation: SR output base layer ke roop mein full-size render hota hai, LR input CSS `clip-path: inset()` se left N% tak hi dikhta hai, aur ek invisible (`opacity-0`) native `<input type="range">` poore container par overlay hota hai jo drag position control karta hai. Visual divider line/handle sirf display ke liye hai (`pointer-events-none`), actual interaction native range input handle karta hai.
**Reasoning:** Native `<input type="range">` use karne se drag/touch/keyboard sab automatically kaam karte hain (accessibility bhi free mein milti hai) — koi extra npm dependency (jaise react-compare-slider) nahi chahiye. Yeh existing "minimal dependencies" spirit (D022) ke saath consistent hai.
**Verification**: `npm run build` clean pass hua (TypeScript errors nahi). Dev server (already running, HMR se changes live the) ke through proxy se real GeoTIFF upload karke confirm kiya ki backend integration abhi bhi kaam karta hai. Visual drag-behavior (slider actually smoothly move karta hai ya nahi) browser mein hi verify ho sakta hai — user ko check karne ke liye bola.
**Alternatives considered:** Manual mousedown/mousemove/mouseup pointer-event handling likhna — reject kiya, native range input same result deta hai kam code aur better accessibility ke saath.
**Status:** Accepted, build-verified. Visual behavior browser mein user confirm karega.

---

## D027 — Accuracy metrics in the UI: only computed when a ground-truth reference is provided, never fabricated
**Date:** 2026-09-08
**Decision:** User ne poocha "kis extent tak image sahi hai" dikhana chahte the. PSNR/SSIM/SAM/ERGAS sab ko ek ground-truth HR reference chahiye compare karne ke liye — real-world upload (koi reference nahi) ke liye yeh genuinely compute nahi ho sakte. Isliye `POST /api/infer` mein ek optional dusra file field add kiya (`hr_reference`) — agar diya gaya, real metrics compute karke return karte hain; nahi diya to `metrics: null`, UI mein saaf keh deta hai "reference nahi diya, metrics available nahi hain" — kabhi bhi fabricate nahi karte.

Metrics computation: SR output (jo already denormalized/physical-scale hai response ke liye) ko `_normalize()` se wapas [0,1] mein convert kiya (D008 ka wahi hr_ranges reuse kiya), reference ko bhi same normalize kiya, phir `compute_all_metrics()` (already-tested `ml/evaluation/metrics.py`) call kiya — bilkul wahi normalization jo training/eval mein har jagah use hoti hai, koi naya ad-hoc scale nahi banaya.
**Verification**: Real LR/HR pair (ROI_0057) upload kiya curl se, poore proxy path (5173→8000) ke through — metrics mile (PSNR 16.73, SSIM 0.196, SAM 15.49°, ERGAS 13.76). SSIM thoda low laga (val-set average ~0.43 se), to cross-check kiya `ml/evaluation/evaluate_checkpoint.py` ka trusted code path use karke isi exact image par — **exact same numbers** aaye (floating-point tak match) — confirm hua ki backend ka metrics wiring sahi hai, low SSIM genuine hai (yeh road/building-heavy patch hai, jahan exact edge-alignment SSIM ko zyada punish karta hai, jo visually bhi consistent hai jo pehle dekha tha). Do edge cases bhi test kiye: (1) reference na diya → `metrics: null`, koi crash nahi; (2) mismatched-shape reference diya → clean 400 error with clear message, crash nahi.
**Reasoning:** Yeh poore project ka core ethos hai (PRD Section 14: "never put fabricated numbers") — real-world deployment mein reference nahi milega, to honestly "unavailable" dikhana zaroori tha fake confidence dikhane ki jagah.
**Alternatives considered:** Uncertainty-model (D016/D018) se confidence map dikhana (jisko ground truth ki zaroorat nahi) — abhi ke liye reject kiya kyunki backend abhi SwinIR serve karta hai (best visual quality ke liye, D020), aur uncertainty-trained EDSR checkpoint ka real Colab run abhi tak nahi hua (Open Considerations mein already tracked). Future improvement ke roop mein note kiya.
**Status:** Accepted. Backend + frontend dono verified end-to-end.

---

## D028 — Quality run complete: metrics roughly flat (as expected), real test is visual
**Date:** 2026-09-08
**Decision:** SwinIR + perceptual loss + ICNR (D023/D024/D025 fixes) training complete kiya — 30 epochs, koi crash nahi (dono memory fixes poore run mein held). Full val-set (n=279) comparison plain-L1 SwinIR (D013) ke against:

| Metric | Plain SwinIR | + perceptual + ICNR |
|---|---|---|
| PSNR | 16.92 dB | 16.83 dB |
| SSIM | 0.429 | 0.437 |
| SAM | 11.60° | 12.07° |
| ERGAS | 14.56 | 13.89 (median 8.90) |

**Reasoning:** Numbers roughly wash hain — PSNR/SAM thoda flat/worse, SSIM/ERGAS thoda better. Yeh exactly literature-consistent hai: perceptual loss known tradeoff hai — pixel-fidelity metrics thodi qurbaan hoti hain perceptual/visual quality ke liye, guaranteed metric-improvement nahi hota. Is run ka asli maqsad metrics improve karna tha hi nahi — checkerboard artifact (D020) kam karna aur visually sharper output dena tha, jo metrics dekh nahi sakte. Real verification ab checkpoint download karke visual comparison se hoga (jaisa D020 mein pehle kiya tha).
**Status:** Training accepted as successful (both D024/D025 fixes verified working end-to-end on real Colab GPU run, no crash). Visual verification pending (user download + rerun demo).

---

## Open Considerations (decided nahi, but track karna hai)

- **Indian HR reference imagery**: Abhi tak koi concrete Indian-AOI paired dataset identify nahi hua. SEN2NAIP US-only (NAIP) hai. Demo ke liye Indian AOI par qualitative (no ground-truth) inference run karna zaroori hoga — isko formal decision banate waqt yahan document karna.
- **Uncertainty estimation method**: PRD MC-ensemble (5x inference) suggest karta hai; single-pass heteroscedastic head (mean+variance in one forward pass) zyada compute-efficient alternative hai. Final choice benchmarking ke baad decide hoga.
- **Backend infra scope for MVP demo**: PostGIS/Redis/Celery vs simpler synchronous/local-storage approach — team ki compute/timeline availability dekh kar decide karna hai.
- **Perceptual loss**: DINOv3 vs standard VGG-based perceptual loss — DINOv3 optional/stretch goal hai per PRD khud bhi.
- **Nodata handling refinement**: Abhi LR nodata pixels ko 0 se replace kiya ja raha hai (D007). Agar training mein edge artifacts dikhein, to proper masking (loss se exclude karna) ya un ROIs ko filter karna consider karna hoga jinme nodata fraction zyada hai.
- ~~**ERGAS outlier investigation**~~ **RESOLVED (D015)**: `ROI_05939` ka ek band (index 2) ka mean sirf 0.0075 hai (likely water/shadow, near-zero reflectance) — ERGAS formula `(RMSE/mean)²` hai per band, to near-zero denominator ek hi patch ka ERGAS 771.5 tak blow-up kar deta hai (median 11.66 ke against). Yeh ERGAS metric ki ek known limitation hai low-reflectance regions ke liye, code bug nahi. Fix: `run_baseline.py`/`evaluate_checkpoint.py` ab median bhi print karte hain mean ke saath, kyunki mean is tarah ke outliers ke against robust nahi hai.
- **Scale SwinIR to match EDSR's parameter count** (from D013): Abhi SwinIR 2.2x chhota hai phir bhi tied hai. Bigger embed_dim ya deeper RSTBs try karna chahiye ek fairer max-capacity comparison ke liye, before final "which architecture wins" call lena.
- **Tune λ_spectral / λ_edge** (from D014): 0.1/0.1 sirf ek starting guess hai. Pehla ablation result dekhne ke baad (better/worse/same), agar promising lage to proper sweep (jaise 0.05/0.1/0.5/1.0) karna chahiye final numbers ke liye.
- **Uncertainty warm-start** (from D016): Agar Colab par full-scale (2,283 pairs, 20 epochs) heteroscedastic training mein bhi instability dikhe (jo local 2-example test mein nahi dikha lr=1e-4 par, lekin bigger scale par naye patterns emerge ho sakte hain), to warm-start approach try karna — pehle plain-L1 EDSR se weights load karke, phir NLL ke saath fine-tune karna.
- ~~**SwinIR tiled inference**~~ **RESOLVED (D018)**.
- ~~**Uncertainty map GeoTIFF output**~~ **RESOLVED (D018)**.
- **Uncertainty calibration on a real-trained checkpoint** (from D018): Abhi tak sirf 4-step smoke-test checkpoint se test hua hai (expected-bad numbers). Colab ke actual 20-epoch uncertainty run ke baad, `uncertainty_calibration()` (D016) ka real number dekhna hai — kya std genuinely error se correlate karta hai.
- **PixelShuffle checkerboard artifact fix** (from D020): ICNR weight initialization ya post-shuffle blur layer add karna `UpsampleBlock` mein (EDSR aur SwinIR dono use karte hain), taaki visible ripple/checkerboard texture kam ho. Demo-presentable hai abhi ke liye, lekin production-quality ke liye fix karna chahiye.
