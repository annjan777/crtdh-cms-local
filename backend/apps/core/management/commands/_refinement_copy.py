"""Copy for the post-redesign refinement pass (26 Nov 2026), used by apply_copy_fixes.

Every factual statement here comes from a named source: the CMS's own objectives table, the CRTDH
membership PDF (facility rates and terms), or a published paper or government release linked in the text.
Nothing is added that a source does not say. REFINEMENT_FIXES replace exact old text; FILLS only set
fields that are still empty, so text an editor has written is never overwritten.
"""

# ---------------------------------------------------------------------------------------------------------
# Old text, exactly as it is in the CMS on 26 Nov 2026 (after the earlier copy fixes).
# ---------------------------------------------------------------------------------------------------------

_MISSION_OLD = (
    "Almost half of the world's population is forced to live without access to basic healthcare, health "
    "education and public health measures — a cycle that pushes millions below the poverty line every year "
    "through health-related expenses. Breaking that cycle means intermingling advances in healthcare technology, "
    "including digital healthcare, with value-added human resource development — the central principle behind "
    "CRTDH's vision at IIT Kharagpur.\n\n"
    "The CRTDH for Affordable Health at IIT Kharagpur was established in 2019 to support MSMEs, startups and "
    "entrepreneurs working in the healthcare domain, offering R&D support, state-of-the-art facilities, a "
    "manufacturing plant and licensing support. In spite of the constraints of the COVID-19 pandemic, CRTDH "
    "developed several point-of-care technologies, trained community health workers, ran medical and validation "
    "camps in remote settings, and set up a Pathology and Imaging Lab in collaboration with an NGO — continuing "
    "to make healthcare accessible to the last-mile population."
)
# WHO and World Bank, Tracking Universal Health Coverage: 2023 Global Monitoring Report (figures for 2021).
_MISSION_NEW = (
    "More than half of the world's population, about 4.5 billion people in 2021, were not fully covered by "
    "essential health services, and about 2 billion faced financial hardship because of what they paid for "
    "health care (WHO and World Bank, Tracking Universal Health Coverage: 2023 Global Monitoring Report). "
    "Closing that gap means combining advances in healthcare technology, including digital health, with "
    "value-added human resource development — the central principle behind CRTDH's vision at IIT Kharagpur.\n\n"
    "The CRTDH for Affordable Health at IIT Kharagpur was established in 2019 to support MSMEs, startups and "
    "entrepreneurs working in the healthcare domain, offering R&D support, facilities, a manufacturing plant "
    "and licensing support. During the COVID-19 pandemic, CRTDH developed point-of-care technologies, trained "
    "community health workers, ran medical and validation camps in remote settings, and set up a pathology and "
    "imaging lab with an NGO."
)

# "18 CRTDHs" and the nationwide expansion could not be verified against a DSIR source, so the number goes.
_INTRO_OLD_P2 = (
    "DSIR-CRTDH is now a strong family of 18 CRTDHs located across the country, working in sectors such as "
    "electronics/renewable energy, affordable health, environmental interventions, low-cost machining and new "
    "materials/chemical processes — all engaged in R&D activity with real societal impact, helping MSMEs remain "
    "competitive while DSIR expands the network across every state and Union Territory."
)
_INTRO_NEW_P2 = (
    "DSIR's CRTDHs work in sectors such as electronics and renewable energy, affordable health, environmental "
    "interventions, low-cost machining and new materials and chemical processes, helping MSMEs carry out R&D "
    "and remain competitive."
)
_INTRO_P1 = (
    "Innovation plays a critical role in shaping the industrial competitiveness of any nation. India, being a "
    "developing nation, has its own set of unique situations and challenges that impede the innovation potential "
    "of MSMEs operating in it. Many of these challenges are related to public policy, funding constraints, access "
    "to suitable equipment, shortage of skilled R&D workforce and weak linkages between institutions and "
    "industry. DSIR has therefore initiated a program aimed at the creation of Common Research & Technology "
    "Development Hubs (CRTDHs) to encourage research and technology development by MSMEs and develop synergy "
    "between academia and industry, facilitating hands-on training, skill development and R&D infrastructure."
)

# Homepage: the same points, half the words (no claim added or removed).
_ENT_OLD = (
    "CRTDH supports MSMEs in developing and manufacturing affordable medical technologies. By helping enterprises "
    "build manufacturing capabilities, the Hub aims to improve access to indigenous healthcare technologies. "
    "CRTDH's pilot-plant facilities support the development and manufacturing of indigenous healthcare "
    "technologies. These capabilities aim to help innovators and enterprises translate research into solutions "
    "for healthcare delivery."
)
_ENT_NEW = (
    "CRTDH helps MSMEs develop and manufacture affordable medical technologies. Its pilot-plant facilities let "
    "innovators and enterprises take indigenous healthcare technologies from research to manufacture."
)
_WOMEN_OLD = (
    "CRTDH, in collaboration with its implementation partner, FIH, has supported technology-enabled healthcare "
    "services in rural communities where access to healthcare facilities may be limited. The initiative supports "
    "community health workers in delivering healthcare services to underserved rural communities. Rural women have "
    "been trained to support patients and coordinate with remote healthcare professionals using affordable "
    "diagnostic technologies. The programme also aims to create opportunities for skills development and "
    "livelihoods."
)
_WOMEN_NEW = (
    "With its implementation partner FIH, CRTDH has supported technology-enabled healthcare in rural communities "
    "with limited access to clinics. Community health workers, many of them rural women trained for the role, "
    "support patients and work with remote doctors using affordable diagnostic technologies, which also builds "
    "skills and livelihoods."
)

# ---------------------------------------------------------------------------------------------------------
# Innovations: a short description, a brief "how it works" where the source gives one, and the evidence
# with its reference. Long step-by-step procedures stay in the CMS; the site shows them folded away.
# ---------------------------------------------------------------------------------------------------------

_ORAL_OLD = (
    "<p>Lifestyle factors in the underserved community.</p><p>Current methods of diagnostics require "
    "sophisticated lab-based procedures.</p><p>A low cost, portable, handheld imaging device to screen oral "
    "cancer and pre-cancer based on measured change in blood flow rate of the tissue from thermal imaging and "
    "analytics.</p><p>Successful phase-I clinical trial with more than 60 patients indicated more than 96.66% "
    "accuracy in detecting oral cancer and pre-cancer.</p><p>The early prototype developed is ready to be "
    "deployed in the field by minor sophistication and automation.</p><p>Method can be extended to other forms "
    "of cancer.</p>"
)
# Bhowmik et al., PNAS 2022: 61 participants; "overall sensitivity >96.66% and specificity of 100%" vs biopsy.
_ORAL_NEW = (
    "<p>A low-cost, portable, handheld device that screens for oral cancer and pre-cancer. It estimates the "
    "blood flow (perfusion) in the tissue from thermal images and analyses it, without a specialised "
    "laboratory. The research team reports that the method could be extended to other forms of cancer.</p>"
    "<h3>Evidence</h3>"
    "<p>In a clinical study of 61 participants at the Guru Nanak Institute of Dental Science and Research, "
    "Kolkata (36 healthy volunteers, 14 people with oral submucous fibrosis, a pre-cancer, and 11 with oral "
    "cancer), the device showed a sensitivity above 96.66% and a specificity of 100% compared with biopsy. "
    "After this first trial the device moved to field trials.</p>"
    '<p>Sources: Bhowmik A, Ghosh B, Pal M, Paul RR, Chatterjee J, Chakraborty S. <a href="https://doi.org/'
    '10.1073/pnas.2026201119">Portable, handheld, and affordable blood perfusion imager for screening of '
    "subsurface cancer in resource-limited settings</a>. PNAS 2022;119(2):e2026201119. "
    '<a href="https://dst.gov.in/infosys-awardee-brings-affordable-diagnostic-technologies-remote-resource-'
    'constrained-areas">Department of Science and Technology, December 2022</a>.</p>'
)

_CHEST_OLD = (
    "<p>This is a deep learning-enabled android app to predict the vulnerable COVID-19 patients based on digital "
    "frontal chest X-ray images. This app is designed to individuate COVID-19 cases from no-findings and "
    "non-COVID Pneumonia. Using this application, you can get the automated classification of frontal chest "
    "X-rays revealing fine-grained variability in appearance that are not distinguishable by Pulmonologist. "
    "Here, deep convolutional neural networks (CNN) were used to accomplish highly variable tasks in many types "
    "of fine-grained objects in the images. For the development of the CNN model, the classification of chest "
    "X-rays was carried out using a single CNN with transfer learning, formed end-to-end from direct images, "
    "using only pixels and disease tags as entries. The used CNN model was trained on a dataset accessed from "
    "public repository consisting of a total of 1697 frontal X-ray images (549 samples of COVID-19, 576 samples "
    "of no findings, and 572 samples of non-COVID pneumonia) with high classification accuracy.</p>"
)
# Same facts, without the claims no source supports (beating pulmonologists, "high accuracy", predicting
# "vulnerable" patients), and stated as a research tool.
_CHEST_NEW = (
    "<p>ChestXAI is a research Android app that sorts a frontal chest X-ray image into one of three groups: "
    "COVID-19, non-COVID pneumonia or no findings.</p>"
    "<h3>How it works</h3>"
    "<p>A deep convolutional neural network (CNN), built with transfer learning, classifies the image from its "
    "pixels alone. It was trained on 1,697 frontal chest X-ray images from a public repository: 549 COVID-19, "
    "572 non-COVID pneumonia and 576 with no findings.</p>"
    "<p>It is a research prototype. It is not a diagnostic test and does not replace a clinician's reading of "
    "the X-ray or a laboratory test for COVID-19.</p>"
)

_COVIRAP_OLD = "<p>COVIRAP: A Nucleic-Acid Based Rapid Diagnostic Test for COVID-19.</p>"
_COVIRAP_NEW = (
    "<p>A portable, low-cost unit that runs a nucleic-acid test for infectious diseases, including COVID-19, "
    "outside a central laboratory. The test is pre-programmed into the unit, finishes within an hour, and a "
    "mobile app shows the result.</p>"
    "<h3>Evidence</h3>"
    "<p>ICMR-NICED validated COVIRAP for COVID-19 detection in October 2020. In 2021 IIT Kharagpur licensed it "
    "for commercial production.</p>"
    '<p>Sources: <a href="https://pib.gov.in/PressReleasePage.aspx?PRID=1666418">Press Information Bureau, '
    '21 October 2020</a>. <a href="https://kgpchronicle.iitkgp.ac.in/?p=7398">KGP Chronicle: global launch of '
    "COVIRAP</a>.</p>"
)

_LIPID_OLD = "<p>Lipidest.</p>"
_LIPID_NEW = (
    "<p>Lipidest measures the full lipid panel (cholesterol and triglycerides) from finger-prick blood at the "
    "point of care.</p>"
    "<h3>How it works</h3>"
    "<p>A portable spinning disc separates plasma from the blood and mixes it with the test reagents; a small "
    "spin box and an ordinary office scanner give the readout, with no specialised instrument.</p>"
    "<h3>Evidence</h3>"
    "<p>Results showed acceptable accuracy against laboratory gold-standard methods. Source: Pakira V, Agarwal R, "
    'Chatterjee S, Mukherjee A, Chakraborty S. <a href="https://doi.org/10.1039/d3ay00412k">Lipidest: a lipid '
    "profile screening test at extreme point of care settings using a portable spinning disc and an office "
    "scanner</a>. Analytical Methods, 2023.</p>"
)

_DISC_OLD = "<p>Testing Blood on a Portable Spinning Disc.</p>"
_DISC_NEW = (
    "<p>A portable spinning disc that runs several tests from a single drop of body fluid. A complete blood "
    "count (CBC) test on this platform has been designed and validated, with an electrochemical sensor that "
    "reads out the result.</p>"
    '<p>Source: <a href="https://dst.gov.in/infosys-awardee-brings-affordable-diagnostic-technologies-remote-'
    'resource-constrained-areas">Department of Science and Technology, December 2022</a>.</p>'
)

_UDAY_OLD = "<p>Clinical Algorithm based App for Delivering Primary Care at Resource Poor Settings &mdash; Uday.</p>"
_UDAY_NEW = (
    "<p>Uday is clinical decision-support software for primary care where there is no doctor on site. "
    "Starting from the patient's medical problem, it guides a community health worker to collect structured, "
    "step-by-step health information, which a remote doctor then reviews.</p>"
    "<p>It was developed with the Foundation for Innovations in Health (FIH) for its rural e-health clinics. "
    'Source: <a href="https://solve.mit.edu/solutions/63981">FIH, Uday – Health for a Billion (MIT Solve)</a>.</p>'
)

_HB_OLD = (
    "<p>Hemoglobin Detection: Screening of Anemia, using a printed microfluidic chip read by a smartphone camera "
    "and app.</p><ol><li>Printed microfluidic chip</li><li>Adding whole blood + diluting reagent to the reaction "
    "pad</li><li>Bluish green colour developed in reaction pad</li><li>Picture of the reaction pad captured with "
    "smartphone camera.</li><li>Picture of the reaction pad captured with smartphone camera.</li><li>In built app "
    "in smart phone performs robust image processing and displaying haemoglobin concentration</li></ol>"
)
_HB_NEW = (
    "<p>A paper-based test for hemoglobin, to screen for anemia, read with a smartphone camera and app. It "
    "uses about 10 µL of finger-prick blood and gives a result within 5 minutes.</p>"
    "<h3>How it works</h3>"
    "<ol><li>Printed microfluidic chip</li><li>Whole blood and diluting reagent are added to the reaction "
    "pad</li><li>A bluish-green colour develops in the reaction pad</li><li>The smartphone camera captures the "
    "reaction pad</li><li>The app analyses the image and shows the hemoglobin concentration</li></ol>"
    "<h3>Evidence</h3>"
    "<p>Tested with 200 venous blood samples in the laboratory and 142 finger-prick samples in the field. "
    "Source: Biswas SK, Chatterjee S, Bandyopadhyay S, Kar S, Som NK, Saha S, Chakraborty S. "
    '<a href="https://doi.org/10.1021/acssensors.0c02361">Smartphone-enabled paper-based hemoglobin sensor for '
    "extreme point-of-care diagnostics</a>. ACS Sensors 2021;6(3):1077–1085.</p>"
)

_GLUCO_OLD = (
    "<p>Blood Glucose Detection on a Printed Paper Strip, from the mobile app that guides the user through the "
    "test, through the paper strip and detection box, to the smartphone-based analysis of the result. See the "
    "project carousel below for the individual components (Mobile App, Paper Strip, Detection Box, Smartphone "
    "based analysis).</p>"
)
_GLUCO_NEW = (
    "<p>A paper-strip test that estimates plasma glucose from one drop of blood, read with a smartphone.</p>"
    "<h3>How it works</h3>"
    "<p>A mobile app guides the user through the test. The paper strip separates plasma from the blood and "
    "develops a colour, a detection box gives even lighting, and the smartphone analyses the image. The project "
    "spotlight on this page shows each part.</p>"
    "<h3>Evidence</h3>"
    "<p>Source: Biswas SK, Chatterjee S, Laha S, Pakira V, Som NK, Saha S, Chakraborty S. "
    '<a href="https://doi.org/10.1039/D2LC00824F">Instrument-free single-step direct estimation of the plasma '
    "glucose level from one drop of blood using smartphone-interfaced analytics on a paper strip</a>. "
    "Lab on a Chip 2022;22(23):4666–4679.</p>"
)

_ANEMIA_OLD = (
    "<ol><li>Apply glycerin on the paper pad of the cartridge with paint brush. Make sure that the glycerin is "
    "completely absorbed within the paper and no surplus volume of glycerin remains on the paper surface.</li>"
)
_ANEMIA_NEW = (
    "<p>A reagent-free anemia screening test. One drop of finger-prick blood is placed on a paper strip wetted "
    "with glycerin; the pattern the blood forms depends on the red-cell content, and a smartphone app analyses a "
    "photo of the pattern.</p>"
    '<p>Source: Laha S, Bandopadhyay A, Chakraborty S. <a href="https://doi.org/10.1021/acssensors.2c00806">'
    "Smartphone-integrated label-free rapid screening of anemia from the pattern formed by one drop of blood on "
    "a wet paper strip</a>. ACS Sensors 2022.</p>"
    "<h3>Test procedure</h3>"
    "<ol><li>Apply glycerin on the paper pad of the cartridge with paint brush. Make sure that the glycerin is "
    "completely absorbed within the paper and no surplus volume of glycerin remains on the paper surface.</li>"
)

_EIS_OLD = "<ol><li>Start with calibrating the impedance analyzer.</li>"
_EIS_NEW = (
    "<p>Measures hematocrit and hemoglobin together from one drop of whole blood, using a disposable paper "
    "strip sensor and a portable impedance reader connected to a smartphone.</p>"
    '<p>Source: Anjali, Das S, Chakraborty S. <a href="https://doi.org/10.1039/d2lc00456a">Simultaneous '
    "quantitative detection of hematocrit and hemoglobin from whole blood using a multiplexed paper sensor with "
    "a smartphone interface</a>. Lab on a Chip 2023.</p>"
    "<h3>Test procedure</h3>"
    "<ol><li>Start with calibrating the impedance analyzer.</li>"
)


REFINEMENT_FIXES = [
    ("core.AboutPage", "mission_vision", _MISSION_OLD, _MISSION_NEW),
    ("core.AboutPage", "intro", f"{_INTRO_P1}\n\n{_INTRO_OLD_P2}", f"{_INTRO_P1}\n\n{_INTRO_NEW_P2}"),
    ("core.HomePage", "enterprises_text", _ENT_OLD, _ENT_NEW),
    ("core.HomePage", "women_text_1", _WOMEN_OLD, _WOMEN_NEW),
    ("innovations.Innovation", "body", _ORAL_OLD, _ORAL_NEW),
    ("innovations.Innovation", "body", _CHEST_OLD, _CHEST_NEW),
    ("innovations.Innovation", "body", _COVIRAP_OLD, _COVIRAP_NEW),
    ("innovations.Innovation", "body", _LIPID_OLD, _LIPID_NEW),
    ("innovations.Innovation", "body", _DISC_OLD, _DISC_NEW),
    ("innovations.Innovation", "body", _UDAY_OLD, _UDAY_NEW),
    ("innovations.Innovation", "body", _HB_OLD, _HB_NEW),
    ("innovations.Innovation", "body", _GLUCO_OLD, _GLUCO_NEW),
    # Media: bare event names get the description the homepage news items already give them.
    ("media_gallery.MediaEvent", "title", "Pathology and Eye Clinic", "CRTDH-supported pathology and eye clinic"),
    ("media_gallery.MediaEvent", "title", "Rural Healthcare Foundation", "CRTDH team visit to the Rural Healthcare Foundation"),
    ("media_gallery.MediaEvent", "title", "Arjun Malhotra",
     "Lab visit by Arjun Malhotra, founder and former chairman of HCL Technologies"),
    ("media_gallery.MediaEvent", "title", "Conclave", "Health awareness programme and conclave"),
    ("media_gallery.MediaEvent", "title", "Chintan Shivir", "Chintan Shivir at CRTDH, IIT Kharagpur"),
    ("media_gallery.MediaEvent", "title", "Other Ongoing Activities", "Other ongoing activities"),
]

# Prefix fixes: the procedure lists are long; only their start is matched, and a short description with
# its source is put in front. (app_label.Model, field, old prefix, new prefix)
PREFIX_FIXES = [
    ("innovations.Innovation", "body", _ANEMIA_OLD, _ANEMIA_NEW),
    ("innovations.Innovation", "body", _EIS_OLD, _EIS_NEW),
]

# ---------------------------------------------------------------------------------------------------------
# Fills for empty fields. Services: from the CMS objectives table and the membership PDF.
# Products: summary from the published paper or release; status "licensed" from IIT Kharagpur's technology-
# transfer list (SNST, which names HealthLedger, IMEDTECH, Huwel and Inno-Dx) and the COVIRAP licence (2021).
# ---------------------------------------------------------------------------------------------------------

_RD = {"title__in": ["R&D support", "R & D support"]}
_PROTO = {"title": "Prototyping and testing facilities"}
_REG = {"title": "Regulatory guidance"}
_TRAIN = {"title": "Training & capacity-building"}
_MARKET = {"title": "Market access opportunities"}
_SCALE = {"title": "Support for scalability and sustainability"}

FILLS = [
    ("services.Service", _RD, "description",
     "Research and development support for MSMEs and startups with a healthcare device, test or service, "
     "from choosing the product to a design that is ready to manufacture."),
    ("services.Service", _RD, "includes",
     "Selecting the product, device or service, based on the MSME's understanding of market needs\n"
     "Data analysis and iterative development\n"
     "Patenting support\n"
     "Developing the product to the design-for-manufacture stage"),
    ("services.Service", _PROTO, "description",
     "Laboratory, prototyping and pilot-plant equipment at IIT Kharagpur that MSMEs and startups can book, "
     "including sterile rooms, PCB prototyping, laser cutting, 3D printing and pilot plants for paper-based devices."),
    ("services.Service", _PROTO, "how_to_access",
     "Book equipment by the hour through CRTDH's annual membership (Platinum, Gold or Silver). Slots depend on "
     "availability, and rates do not include consumables or consultancy."),
    ("services.Service", _REG, "description",
     "Help for MSMEs taking a medical device or test through certification and regulatory clearance."),
    ("services.Service", _REG, "includes",
     "Guidance through the certification process\n"
     "CDSCO, DCGI, CE, ISI and BIS clearances, as appropriate"),
    ("services.Service", _TRAIN, "description",
     "Hands-on training for MSMEs in prototype development using CRTDH facilities."),
    ("services.Service", _TRAIN, "includes",
     "Hands-on prototype development in CRTDH facilities\n"
     "The fundamentals of the device's technology platform and how it works"),
    ("services.Service", _MARKET, "description",
     "Routes to validation and first sales for a new product, through IIT Kharagpur's healthcare network."),
    ("services.Service", _MARKET, "includes",
     "Access to the rural healthcare network and super-speciality hospitals for an initial validation study\n"
     "Access to multi-centre trials with the appropriate ethics (IRB) clearances\n"
     "Sales support through IIT Kharagpur's rural healthcare network, to build initial confidence"),
    ("services.Service", _SCALE, "description",
     "Technology transfer and pilot manufacturing, to take a validated product towards production."),
    ("services.Service", _SCALE, "includes",
     "Technology transfer to MSMEs through royalty-share agreements\n"
     "Pilot plants for lateral-flow and paper-based devices"),

    ("products.Product", {"name": "Gluco QR"}, "summary",
     "A paper-strip test that estimates plasma glucose from one drop of finger-prick blood, read with a "
     "smartphone app."),
    ("products.Product", {"name": "Sense-Hb"}, "summary",
     "A paper-based hemoglobin test read with a smartphone app. It uses about 10 µL of finger-prick blood and "
     "gives a result within 5 minutes."),
    ("products.Product", {"name": "Oral Cancer"}, "summary",
     "A portable, handheld imager that screens for oral cancer and pre-cancer by estimating the blood flow in "
     "the tissue from thermal images."),
    ("products.Product", {"name": "COVIRAP"}, "summary",
     "A portable unit for nucleic-acid testing of infectious diseases, including COVID-19, with results within "
     "an hour. Validated by ICMR-NICED in 2020."),
    *[("products.Product", {"name": n}, "status", "licensed")
      for n in ("Gluco QR", "Sense-Hb", "Oral Cancer", "Hemomeasure", "COVIRAP")],
]
