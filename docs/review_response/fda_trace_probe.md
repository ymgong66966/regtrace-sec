# FDA Warning-Letter Trace Probe

This probe checks whether the public FDA warning-letter corpus can support a
RegTrace-style cross-regulatory extension. It is a data-structure probe, not a
labeling experiment.

## Headline

- Total records: 6428
- Warning-letter rows: 5220
- Closeout-letter rows: 1200
- Rows with a public `response_letter` field: 1
- Warning rows linking to a closeout letter: 413
- Linked warning-closeout pairs with closeout text in the corpus: 413
- Linked closeout URLs missing from corpus: 0
- Candidate JSONL: `data/fda_warning_letters/fda_warning_closeout_trace_candidates.jsonl`

## Interpretation

The FDA data is promising as a cross-domain regulatory trace resource, but it
does not mirror the SEC task one-to-one. Public warning letters frequently link
to later closeout letters, while public company response letters are almost
absent in this snapshot. The strongest near-term FDA task is therefore not
`request + company response + amended evidence -> resolved`. It is closer to:

1. `warning letter -> closeout/outcome trace` for studying regulatory-resolution
   language and time-to-closeout;
2. `warning letter + closeout letter -> deficiency-resolution verification`,
   possibly with contrastive negatives; or
3. positive-unlabeled prediction of whether a warning letter eventually receives
   a public closeout letter.

For the current ARR paper, this supports the broader claim that RegTrace-style
context-to-feedback review can generalize beyond SEC correspondence, but it
should be framed as an extension/probe unless we build FDA-specific labels.

## Delay

- Pairs with parseable nonnegative delay: 413
- Median days to closeout: 306
- Min days to closeout: 11
- Max days to closeout: 1793

## Warning Year Distribution

| value | count |
| --- | ---: |
| 2021 | 172 |
| 2022 | 109 |
| 2023 | 53 |
| 2024 | 45 |
| 2025 | 29 |
| 2026 | 5 |

## Product Distribution for Linked Pairs

| value | count |
| --- | ---: |
| Tobacco | 97 |
| Food & Beverages | 79 |
| Drugs | 73 |
| Medical Devices | 69 |
| Drugs / Food & Beverages | 28 |
| Biologics | 16 |
| Animal & Veterinary / Food & Beverages | 15 |
| Dietary Supplements | 14 |
| Animal & Veterinary | 7 |
| Animal & Veterinary / Drugs | 5 |
| Dietary Supplements / Food & Beverages | 4 |
| Dietary Supplements / Drugs | 2 |

## Issuing Office Distribution for Linked Pairs

| value | count |
| --- | ---: |
| Center for Tobacco Products | 98 |
| Center for Devices and Radiological Health | 58 |
| Center for Food Safety and Applied Nutrition (CFSAN) | 24 |
| Center for Drug Evaluation and Research / CDER | 21 |
| Center for Drug Evaluation and Research (CDER) | 12 |
| Center for Biologics Evaluation and Research (CBER) | 10 |
| Division of Human and Animal Food Operations East VI | 9 |
| Division of Human and Animal Food Operations East II | 8 |
| Center for Veterinary Medicine | 8 |
| Division of Human and Animal Food Operations West III | 8 |
| Human Foods Program | 7 |
| Division of Pharmaceutical Quality Operations III | 6 |

## Subject Distribution for Linked Pairs

| value | count |
| --- | ---: |
| Family Smoking Prevention and Tobacco Control Act/Adulterated/Misbranded | 98 |
| New Drug/Misbranded | 30 |
| Unapproved New Drugs/Misbranded | 22 |
| CGMP/Finished Pharmaceuticals/Adulterated | 22 |
| CGMP/QSR/Medical Devices/Adulterated | 21 |
| CGMP/Food/Prepared, Packed or Held Under Insanitary Conditions/Adulterated | 18 |
| Foreign Supplier Verification Program (FSVP) | 16 |
| Investigational Device Exemptions (IDE)/Premarket Approval Application (PMA) Adulterated Device | 14 |
| Compounding Pharmacy/Adulterated Drug Products | 11 |
| Failure to Register and List/Misbranded | 10 |
| CGMP/Active Pharmaceutical Ingredient (API)/Adulterated | 9 |
| Seafood HACCP/CGMP for Foods/Adulterated/Insanitary Conditions | 9 |

## Samples

### Candidate 1: 10057223 Canada Inc. dba Maddog Juice
- Product: Tobacco
- Subject: Family Smoking Prevention and Tobacco Control Act/Adulterated/Misbranded
- Warning date: 2021-11-05
- Closeout date: 2022-06-10
- Days to closeout: 217
- Warning URL: https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/warning-letters/10057223-canada-inc-dba-maddog-juice-620717-11052021
- Closeout URL: https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/warning-letters/10057223-canada-inc-dba-maddog-juice-620717-06102022

**Warning excerpt**

> WARNING LETTER 10057223 Canada Inc. dba Maddog Juice MARCS-CMS 620717 — November 05, 2021 More Warning Letters Warning Letters About Warning and Close-Out Letters Delivery Method: VIA Electronic Mail Product: Tobacco Recipient: Recipient Name David Di Lallo 10057223 Canada Inc. dba Maddog Juice (b)(6) United States (b)(6) info@maddogjuice.com Issuing Office: Center for Tobacco Products United States November 5, 2021 WARNING LETTER Dear David Di Lallo: The Center for Tobacco Products of the U.S. Food and Drug Administration (FDA) recently reviewed the website https://www.maddogjuice.com and determined that the e-liquid products listed there are manufactured and offered for sale or distribution to customers in the United States. Under section 201(rr) of the Federal Food, Drug, and Cosmetic Act (FD&C Act) (21 U.S.C. § 321(rr)), these products are tobacco products because they are made or de

**Closeout excerpt**

> CLOSEOUT LETTER 10057223 Canada Inc. dba Maddog Juice MARCS-CMS 620717 — June 10, 2022 More Warning Letters Warning Letters About Warning and Close-Out Letters Delivery Method: VIA Electronic Mail Reference #: RW2101672 Product: Tobacco Recipient: Recipient Name David Di Lallo 10057223 Canada Inc. dba Maddog Juice United States Issuing Office: Center for Tobacco Products United States Dear David Di Lallo: The United States Food and Drug Administration’s (FDA) Center for Tobacco Products has completed an evaluation of your corrective actions included in your response dated April 13, 2022 to our Warning Letter dated November 5, 2021. Based on our evaluation, it appears that you have taken steps to address the violations contained in the Warning Letter regarding your website https://www.maddogjuice.com. This letter does not relieve you or your firm from the responsibility of taking all nece
### Candidate 2: 1st Phorm LLC
- Product: Drugs
- Subject: Unapproved New Drugs/Misbranded
- Warning date: 2021-07-29
- Closeout date: 2022-02-08
- Days to closeout: 194
- Warning URL: https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/warning-letters/1st-phorm-llc-613715-07292021
- Closeout URL: https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/warning-letters/1st-phorm-llc-613715-02082022

**Warning excerpt**

> WARNING LETTER 1st Phorm LLC MARCS-CMS 613715 — July 29, 2021 More Warning Letters Warning Letters About Warning and Close-Out Letters Delivery Method: VIA UPS Product: Drugs Recipient: Recipient Name Andrew Frisella Recipient Title CEO 1st Phorm LLC 2091 Fenton Logistics Park Blvd Fenton , MO 63026 United States Issuing Office: Office of Human and Animal Food West Division II United States July 29, 2021 Reference CMS #: 613715 WARNING LETTER Dear Mr. Frisella, This letter is to advise you that the U.S. Food and Drug Administration (FDA) reviewed your website at the Internet address www.1stphorm.com in March 2021. Based on our review of your website, we have found serious violations of the Federal Food, Drug, and Cosmetic Act (the Act) and applicable regulations. As explained further below, introducing or delivering the products discussed below for introduction into interstate commerce v

**Closeout excerpt**

> CLOSEOUT LETTER 1st Phorm LLC MARCS-CMS 613715 — February 08, 2022 More Warning Letters Warning Letters About Warning and Close-Out Letters Delivery Method: VIA UPS Product: Dietary Supplements Food & Beverages Recipient: Recipient Name Andrew Frisella Recipient Title CEO 1st Phorm LLC 2091 Fenton Logistics Park Blvd Fenton , MO 63026 United States Issuing Office: Office of Human and Animal Food West Division II United States Dear Mr. Andrew Frisella, The Food and Drug Administration has completed an evaluation of 1st Phorm LLC corrective actions in response to our Warning Letter (CMS case #: 613715) on July 29, 2021. Based on our evaluation, it appears that you have addressed the violation(s) contained in this Warning Letter. Future FDA inspections and regulatory activities will further assess the adequacy and sustainability of these corrections. This letter does not relieve you or your
### Candidate 3: 2m Associates, Inc.
- Product: Food & Beverages
- Subject: Foreign Supplier Verification Program (FSVP)
- Warning date: 2021-07-20
- Closeout date: 2022-04-12
- Days to closeout: 266
- Warning URL: https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/warning-letters/2m-associates-inc-614195-07202021
- Closeout URL: https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/warning-letters/2m-associates-inc-614195-04122022

**Warning excerpt**

> WARNING LETTER 2m Associates, Inc. MARCS-CMS 614195 — July 20, 2021 More Warning Letters Warning Letters About Warning and Close-Out Letters Delivery Method: VIA UNITED PARCEL SERVICE Product: Food & Beverages Recipient: Recipient Name Mr. Alpha Bah Recipient Title C.E.O. and Owner 2m Associates, Inc. 203 W. 140th St, Apt. 4C New York , NY 10030 United States Issuing Office: Division of Northeast Imports United States WARNING LETTER CMS # 614195 Date: 7/20/2021 Dear Mr. Bah: On February 1, 2021 through March 3, 2021, the Food and Drug Administration (FDA) conducted a remote Foreign Supplier Verification Program (FSVP) inspection of 2m Associates Inc. located at 523 Casanova Street, Bronx, NY 10474. We also conducted an initial inspection on April 12, 2019. These inspections were conducted to determine compliance with the requirements of section 805 of the Federal Food, Drug, and Cosmetic

**Closeout excerpt**

> CLOSEOUT LETTER 2m Associates, Inc. MARCS-CMS 614195 — April 12, 2022 More Warning Letters Warning Letters About Warning and Close-Out Letters Product: Food & Beverages Recipient: Recipient Name Mr. Alpha Bah Recipient Title C.E.O. and Owner 2m Associates, Inc. 203 W. 140th St Apt. 4c New York , NY 10030 United States Issuing Office: Division of Northeast Imports United States Dear Mr. Alpha Bah: The Food and Drug Administration has completed an evaluation of your firm’s corrective actions in response to our Warning Letter CMS# 614195 issued on 7/20/2021. Based on our evaluation, it appears that you have addressed the violation contained in this Warning Letter. Future FDA inspections and regulatory activities will further assess the adequacy and sustainability of these corrections. This letter does not relieve you or your firm from the responsibility of taking all necessary steps to assu
### Candidate 4: AcelRx Pharmaceuticals, Inc.
- Product: Drugs
- Subject: False & Misleading Claims/Misbranded
- Warning date: 2021-02-11
- Closeout date: 2022-03-28
- Days to closeout: 410
- Warning URL: https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/warning-letters/acelrx-pharmaceuticals-inc-613257-02112021
- Closeout URL: https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/warning-letters/acelrx-pharmaceuticals-inc-613257-03282022

**Warning excerpt**

> WARNING LETTER AcelRx Pharmaceuticals, Inc. MARCS-CMS 613257 — February 11, 2021 More Warning Letters Warning Letters About Warning and Close-Out Letters Product: Drugs Recipient: Recipient Name Vincent J. Angotti Recipient Title Chief Executive Officer AcelRx Pharmaceuticals, Inc. 351 Galveston Drive Redwood City , CA 94063 United States Issuing Office: The Office of Prescription Drug Promotion (OPDP) United States RE: NDA 209128 DSUVIA (sufentanil) sublingual tablet, CII MA 18, 23 WARNING LETTER Dear Mr. Angotti: The Office of Prescription Drug Promotion (OPDP) of the U.S. Food and Drug Administration (FDA) has reviewed an “SDS Banner Ad” (banner) (PM-US-DSV-0018) and a tabletop display (PM-US-DSV-0049) (display) for DSUVIA (sufentanil) sublingual tablet, CII (Dsuvia) submitted by AcelRx Pharmaceuticals, Inc. (AcelRx) under cover of Form FDA 2253. The promotional communications, the ba

**Closeout excerpt**

> CLOSEOUT LETTER AcelRx Pharmaceuticals, Inc. MARCS-CMS 613257 — March 28, 2022 More Warning Letters Warning Letters About Warning and Close-Out Letters Product: Drugs Recipient: Recipient Name Vincent J. Angotti Recipient Title Chief Executive Officer AcelRx Pharmaceuticals, Inc. 25821 Industrial Blvd. Ste 400 Hayward , CA 94545 United States Issuing Office: The Office of Prescription Drug Promotion (OPDP) United States Dear Mr. Angotti: The Food and Drug Administration has completed evaluation of your firm’s corrective actions in response to our Warning Letter dated February 11, 2021. Based on our evaluation, it appears that you have addressed the violations contained in this Warning Letter. Future FDA surveillance will further assess the adequacy and sustainability of these corrections. This letter does not relieve you or your firm from the responsibility of taking all necessary steps 
### Candidate 5: Aceva, LLC
- Product: Dietary Supplements
- Subject: Unapproved New Drugs/Misbranded
- Warning date: 2021-09-07
- Closeout date: 2021-11-03
- Days to closeout: 57
- Warning URL: https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/warning-letters/aceva-llc-614539-09072021
- Closeout URL: https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/warning-letters/aceva-llc-614539-11032021

**Warning excerpt**

> WARNING LETTER Aceva, LLC MARCS-CMS 614539 — September 07, 2021 More Warning Letters Warning Letters About Warning and Close-Out Letters Delivery Method: United Parcel Service Product: Dietary Supplements Recipient: Recipient Name Mr. Joseph Esposito Recipient Title CEO Aceva, LLC 624 West Glen Ave. Peoria , IL 61614 United States Issuing Office: Center for Food Safety and Applied Nutrition (CFSAN) United States Federal Trade Commission WARNING LETTER RE: 614539 Dear Mr. Joseph Esposito: This is to advise you that the Food and Drug Administration (FDA) reviewed your website at https://aceva.com/ in August 2021 and has determined that you take orders there for your Sugar Balance product. In addition, FDA reviewed your social media websites, https://twitter.com/acevahealth and https://www.facebook.com/acevanutrition, which direct consumers to your website https://aceva.com/ to purchase you

**Closeout excerpt**

> CLOSEOUT LETTER Aceva, LLC MARCS-CMS 614539 — November 03, 2021 More Warning Letters Warning Letters About Warning and Close-Out Letters Product: Dietary Supplements Recipient: Recipient Name Mr. Joseph Esposito Recipient Title CEO Aceva, LLC 624 West Glen Ave. Peoria , IL 61614 United States Issuing Office: Center for Food Safety and Applied Nutrition (CFSAN) United States Dear Mr. Joseph Esposito: The Food and Drug Administration (FDA) has completed an evaluation of your firm’s corrective actions in response to our Warning Letter Re: 614539, issued September 7, 2021. Based on our evaluation, it appears you have addressed the violation(s) contained in the Warning Letter. Future FDA inspections and regulatory activities will further assess the adequacy and sustainability of these corrections. This letter does not relieve you or your firm from the responsibility of taking all necessary st
