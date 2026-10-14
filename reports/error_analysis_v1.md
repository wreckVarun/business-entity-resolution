# Error analysis (validation)

Decision rule: best candidate if p >= 0.725, further candidates if p >= 0.725, each Source 2/3 record given to one Source 1 entity at most.

Correct links: 413,745. False links: 4,059. Missed links among candidates: 15,363. True links lost in blocking: 28,548.

## False links (predicted match, not a match)

| count | country_US_share | target_name_nonlatin | target_addr_missing | house_no_differs |
|---|---|---|---|---|
| 4059.0 | 0.4 | 0.095 | 0.137 | 0.624 |

| country | s1_name | s1_address | target_name | target_address | p |
|---|---|---|---|---|---|
| India | JU Colonisers Private Limited | Sno. 121/2B1, Plot No 44, Deshmukh Plaza, Ahmednagar, Ahmed Nagar, Maharashtra | Limited JU Cólonisers | Sno. 121/2B6, Ahmednagar, महाराष्ट्र, Ahemadnagar | 0.952 |
| US | NB Rmg, Inc | 3621 Harmann Estates Drive, Bridgeton, MO | XNB Rmío, Inc | 3621 Harmann Estates Dr, Bridgeton, Missouri | 0.925 |
| US | Cassey Rodriguez Total Insurance Inc | 21611 Old Barrington Road, North Barrington, IL | Cassey Rodriguez Tota1 Insurance Ltd | 21620 Old Barrington Rd, Barrington, Illinois | 0.761 |
| India | CC Feeds Private Limited | B-86, G/F, F/P Okhla Industrial Area, Ph-Ii, Delhi, New Delhi, Delhi | CC Feeds Limited | B-88, G/f, F/p Okhla Industrial Area, Ph-ii, Delhi, New Delhi, DL | 0.845 |
| India | United Management Private Limited | Sq, A 173, Dlf M1, Sec 1, Near Imt Manesar Chowk, Manesar, Gurgaon, Haryana | Limited United Management Electronics Partners | A 173, Dlf M1, Sec 1, Near Imt Manesar Chowk, Manesar, No 91 Sq, HR, Gurgaon | 0.766 |
| US | Sande Wilson, DMD, P.C. of Asheville | 360 Hilliard Avenue, Unit 301, Asheville, NC | Sande Wigslmfn DUD P.C. of Asheville | NC, ASHEVILLE, 381 HILLIARD AVE | 0.9 |
| India | Ksn Infrastructure | Door No: Iv/ 109, Nedungad Nayarmbalam P O, Ernakulam, Kerala | Ksn  Infrastructure #20390 | None | 0.942 |
| India | Highland Technology Limited | Sr No 7/1, Om Sai Residency, Gurunanak Nagar, Therga, Pune City, Pune, Maharashtra | Highland Technology Private Limited | SR NO D/7/8, OM SAI RESIDENCY, GURUNANAK NAGAR, THERGA, PUNE CITY, महाराष्ट्र | 0.798 |
| India | Seven Engineering Private Limited | C/O Adani Corporate House, Shantigram, S.G Highway, Daskroi, Ahmedabad, Gujarat | Brixgild | Adani Corporate House, Shantigram, S.G Highway, Daskroi, Ahmedabad, Gujarat | 0.883 |
| US | QM Telecommunication | 7442 La Porte Road, Waterloo, IA | QM Telecommunication Inc. | None | 0.83 |
| US | Lambeth, Lorrayne, CPA, P.C. | 412 Oak Street, Cobden, IL | Lambeth, Lorrayne, P.C. Co Cénter | 421-A Oak Street, Cobden, Illinois | 0.873 |
| US | Forsyth, Gavrielle M., DO | 3036 Peppertree Trail, Fort Wayne, IN | Forsyth, Gávrielle M., DO | None | 0.941 |

## Missed links that were candidates

| count | country_US_share | target_name_nonlatin | target_addr_missing | house_no_differs |
|---|---|---|---|---|
| 15363.0 | 0.535 | 0.08 | 0.279 | 0.599 |

| country | s1_name | s1_address | target_name | target_address | p |
|---|---|---|---|---|---|
| India | Asahi International Private Limited | 401 Amit Industrial Estate61 Dr Rao Road, Mumbai, Maharashtra | Asahi International Private | 399 Amit Industrial Estate61 Dr Rao Road, Mumbai, MH | 0.12 |
| India | SSD Infocomm Private Limited | B1-904, Ahmedabad, Sangath Skyz, Koteshwar, Motera, Ahmedabad, Gujarat | Miravantage | Bd/1-904, Sangath Skyz, Koteshwar, Motera, Ahmedabad, GJ | 0.579 |
| India | Jai Golden Engineering LLP | Dada Bazarbhartiya Krida Mandir 57 Naigaon Cross Rd Wadala(W), Mumbai, Maharashtra, Mumbai | जय गोल्डन इंजीनियरिंग एलएलपी | MUMBAI, BOMBAY, Maharashtra, DADA BAZARBHARTIYA KRIDA MANDIR D/57 NAIGAON CROSS RD WADALA(W) | 0.613 |
| US | Walker Big | 3008 Woodland Elm Cove, Lakeland, TN | Weabdkre Big | 3008-A Woodland Elm Cv, N/A, ARLNGTON CITY, TN | 0.328 |
| US | Piper and Jamerson Optics | 419 Anderson Street, Sandusky, OH | Piper ánd Jamerson Optics Inc | 00419 Anderson St, Sandusky, Ohio | 0.14 |
| US | Housing Council Inc. | Unit 2, Spencer, MA, 24 Main Street | Housing-Council-Inc. | None | 0.216 |
| India | NUZ Housing Private Limited | Ground Floor, No. 655, B.M.Road, Chamraj Nagar, Bangarpet, Kolar, Karnataka | Prite NUZ Housing Limited | Karnataka, H.NO 59 GROUND FLOOR, KOLAR, BANGARPET | 0.568 |
| US | Wilmington Quality Newbridge LLC | 181 Cape May Drive, Wilmington, OH | Xylobrix | 181 Cape May Dr, NULL, Wilmington, Ohio | 0.176 |
| US | Rhea Harrison Select Silverbox | 637 Hawk View, Clemmons, NC | Rhea Hardrgcn Select Silverbox | null, 637-641 HAWK VIEW, NC, CLEMMONS | 0.635 |
| India | Green Producer Private Limited | Nr Part Plot No- 01 Vivek, Vihar Colony Roorke Road, Meerut, Uttar Pradesh | Green Producer Limited (Private) | None | 0.006 |
| US | Esma Rascon Jab, LLC | 1514 Hideaway Lane, Lindale, TX | Esma Rascon Jab,  LLC | None | 0.513 |
| US | Rogers Blue Neuberger LP | 815 Elmhurst Lane, Portsmouth City, VA | Rogers Blue Neuberger | None | 0.151 |

## True links lost in blocking

| count | country_US_share | target_name_nonlatin | target_addr_missing | house_no_differs |
|---|---|---|---|---|
| 28548.0 | 0.454 | 0.291 | 0.301 | 0.386 |

| country | s1_name | s1_address | target_name | target_address |
|---|---|---|---|---|
| US | Beth Zion | 2417 U Street, Sacramento, CA | DÉLTANYLA | U ST, SACRAMENTO, CA |
| India | Seven Foundation Limited | 49/1, Venkatakrishna Road, Coimbatore South, Coimbatore, Tamil Nadu | செவன் ஃபவுண்டேஷன் லிமிடெட் | 49/1, COIMBATORE SOUTH, KANIYUR, தமிழ்நாடு |
| India | Golden Brothers Private Limited | C-136 Old-136, Kh No-265, Gf Gali No-22 Gokalpur, Delhi North East, North West Delhi, Delhi | GOLDEN BROTHERS PRIVATE LTD | None |
| India | COW Jewellery Private Limited | 3, Site No.117, 13Th Cross, Telecom Layout, Srirampura, Jakkur Post, Bangalore, Karnataka | Synqu0 | C-3, BANGALORE, ಕರ್ನಾಟಕ |
| India | Jai Infrastructure Private Limited | 1185/4, Kucha Mahajani Chandni Chowk, Delhi, North East, Delhi | जय इंफ्रास्ट्रक्चर प्राइवेट लिमिटेड | PLOT 233 1185/4, KUCHA MAHAJANI CHANDNI CHOWK, DELHI, NORTH EAST, Delhi |
| India | Red Ventures Private Limited | Rajasthan, Jaipur, Banipark, Gokul Apartment, E-3A Kanti Chandra Road, G-1 | रेड वेंचर्स प्राइवेट लिमिटेड | G-1, BANIPARK, JAIPUR, Rajasthan |
| India | Dcode Trading Private Limited | No.139, 411 3Rd Floor, Old Airport Road, Kodihalli, Bangalore North, Bangalore, Karnataka | dcodetrading.com | Bangalore, ಕರ್ನಾಟಕ, 411 3Rd Floor, Old Airport Road, Kodihalli, null, 139 |
| India | All Enterprises Private Limited | A-72-73, Fiee Complex, Okhla Industrial Area, Phase-Ii, New Delhi, South West Delhi, Delhi | ऑल एंटरप्राइजेज प्राइवेट लिमिटेड | A-70-73, New Delhi, South West Delhi, दिल्ली |
| India | Services Aryavrata Call Private Limited | Pocket-4, Mayur Vihar, Phase-Iii, Delhi, East Delhi, Delhi, D-12 | Nexzeta | D-12, Pocket-4, Mayur Vihar, Phase-iii, Delhi, East Delhi, DL |
| India | Creative Developers Private Limited | 1, Ho Chi Minh Sarani 8Th Floor, Metro Plaza, Kolkata, Kolkata, Howrah, West Bengal | ক্রিয়েটিভ ডেভেলপারস প্রাইভেট লিমিটেড | 1, KOLKATA, HOWRAH, West Bengal |
| India | Ags Constructions Pvt. Ltd. | House No. 1793/A, J. B. Road, Dhule, Maharashtra | agsc0nstructions.com | House No. 1793/A, Mumbai, महाराष्ट्र |
| India | One Business Pvt Ltd | Plot No. J 2, Valsad, Umbergaon, Gidc, Umbergam Gidc, Umbergam, Gujarat | ONE BÚSINESS PVT LIMITED | None |
