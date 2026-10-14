# Error analysis (validation)

Decision rule: best candidate if p >= 0.675, further candidates if p >= 0.7, each Source 2/3 record given to one Source 1 entity at most.

Correct links: 418,453. False links: 3,676. Missed links among candidates: 10,655. True links lost in blocking: 28,548.

## False links (predicted match, not a match)

| count | country_US_share | target_name_nonlatin | target_addr_missing | house_no_differs |
|---|---|---|---|---|
| 3676.0 | 0.399 | 0.098 | 0.163 | 0.558 |

| country | s1_name | s1_address | target_name | target_address | p |
|---|---|---|---|---|---|
| India | Calicut Solutions Private Limited | Virkar Dairy Farm Shed, 414-1, Devapur Road- Sakasne Wasti Junction, Virkarwadi, Man, Satara, Maharashtra | Calicut Solutions Limited Limited | None | 0.739 |
| India | United Consultants Private Limited | D. No. 16-11-477/1 To 5, 4Th Floor, Cn Reddy Complex, Opposite Rs Brothers, Pillar No. A1523, Dilsukh Nagar Main Road, Hanuman Nagar, Amberpet, Hyderabad, Telangana | United Cnosultatns  Limited | #16-11-477/6 TO 5, 4TH FLOOR, CN REDDY COMPLEX, OPPOSITE RS BROTHERS, PILLAR NO. A1523, DILSUKH NAGAR MAIN ROAD, HANUMAN NAGAR, AMBERPET, Telangana | 0.992 |
| US | Metropolitan League LP | 9717 October Glory Lane, Rowlett, TX | Metropolitan League LP | None | 0.794 |
| US | Liddy, Winchester & Fernandez | 4727 Ladywood Bluff Drive, IN, Indianapolis | Liddy, Winchester (&) | None | 0.905 |
| India | International International | Cl-01-01-06 12Th Schemeshivaji Nagar Garkheda Parisar, Aurangabad, Maharashtra | इंटरनेशनल इंटरनेशनल लिमिटेड | CL-01-01-06 25TH SCHEMESHIVAJI NAGAR GARKHEDA PARISAR, HOSHIARPUR, AURANGABAD, महाराष्ट्र | 0.977 |
| India | India Classic Play LLP | Sector-9 Huda, House No. 568, Haryana, Ambala City, Ambala | India Classic  Services LLP | HOUSE NO. 589, SECTOR-9 HUDA, AMBALA CITY, Haryana | 0.905 |
| US | ADY Iheartmedia | 716 2nd Street, Nashville, TN | ADJY Ihgraarbtmadia | 716 Second St, Nashville, Tennessee | 0.953 |
| India | New Delhi Pipes LLP | B-65 Gate No 1Naraina Indl.Area Phase Ii, New Delhi, West Delhi, Delhi | New Delhi Company Center | B-65 Gate No 1Naraina Indl.area Phase Ii, West Delhi, New Delhi, दिल्ली | 0.996 |
| India | Kaverita Edge Pvt Ltd | Tamil Nadu, Coimbatore, 256/1, Kaliapuram Sulur, Coimbatore | Kaveriova Edbrdge Pvt Ltd | Coimbatore, TN, 56/1, Kaliapuram Sulur, Coimbatore | 0.81 |
| India | Essential Vidyalaya | 9-4-22/1, 3Rd Floor, Nehru Nagar, Sirsilla, Karim Nagar, Telangana | Essential Vidyalaya Limited | D/9-4-22/6, 3RD FLOOR, NEHRU NAGAR, SIRSILLA, NULL, తెలంగాణ | 0.938 |
| India | VII Beverages Private Limited | H.No.2742, Ozar Shiwar, Taluka Niphad, Niphad, Nashik, Maharashtra | VNI Beverages Prívate Ltd | No, Niphad, Nashik, महाराष्ट्र | 0.753 |
| US | Lower Ready Inc. | AZ, Douglas, 536 6th Street | lower ready inc | DUGLAS TOWNSHIP, 547 6TH SAINT, AZ | 0.827 |

## Missed links that were candidates

| count | country_US_share | target_name_nonlatin | target_addr_missing | house_no_differs |
|---|---|---|---|---|
| 10655.0 | 0.509 | 0.091 | 0.388 | 0.445 |

| country | s1_name | s1_address | target_name | target_address | p |
|---|---|---|---|---|---|
| India | Engineering (india) Ltd | M-1043, Sec-M, Ashiyana- Lucknow, Lucknow, Uttar Pradesh | Engineering  (india) Ltd | None | 0.599 |
| US | QL All Services LLC | 144 Main Street, Agra, KS | Halolyra | 14 MAIN STREET, PMB 569, AGRA, KS | 0.058 |
| US | Strategic Better Oncology LLC | 218 Markus Drive, Shiloh, IL | Strategic Better-Oncology L.L.C. L.L.C. | 215-219 MARKUS DRIVE, PO BOX 1852, SHILOH, IL | 0.085 |
| India | Sai Foods Private Limited | Dholpur, Rajakhera, Kayasth Parqa, Rajasthan, Co Jagan Nath Prakash | Smt Sai Foods Private | Rajasthan, H.NO 354 CO JAGAN NATH PRAKASH, KAYASTH PARQA, RAJAKHERA | 0.385 |
| US | The Dent Deli | 1611 Parkview Avenue, Ozark, MO | The Dént Deli | None | 0.036 |
| US | Dermatology Sterling Partners LLC | 7407 Charlotte Street, Fairfax County, VA | Jaxdrexdova | VA, 7407 CHARLOTTE STREET, FAIRFAX COUNTY | 0.611 |
| US | MA Highland Bulkers Inc | 1015 8th Street, Roanoke Rapids, NC | MA Highland Bulkers Inc | None | 0.225 |
| India | Alco Foundation | 70 Ff Tpt Centre Rohtak Roadpunjabi Bagh, New Delhi, North Delhi, Delhi | Alco-Foundation Ltd | ##344 Ff Tpt Centre Rohtak Roadpunjabi Bagh, New Delhi, North Delhi, DL | 0.139 |
| India | Supreme It Private Limited | Kharavali Nagar Dawle, H.No.17 Bharatyadav Chawl, Maharashtra, Thane | Praie Supreme It (Limited) | H.no.1-7 Bharatyadav Chawl, Thane, MH | 0.075 |
| India | Anas Packers Limited | 2, Senguptha Streetram Nagar Coimbatore 9, Coimbatore, Tamil Nadu | Ltd Anas Packers | 9-2, Coimbatore, Ramnagar, தமிழ்நாடு | 0.525 |
| India | Supreme Business Private Limited | Flat No Qu-211-B, Pitam Pura, Delhi, North West, Delhi | Supreme Business  Private Limited | None | 0.067 |
| US | Premier Advanced Omega Inc. | 8808 Blomberg Street, Fl 1, Olympia, WA | Premier Advanced Omega Inc | None | 0.613 |

## True links lost in blocking

| count | country_US_share | target_name_nonlatin | target_addr_missing | house_no_differs |
|---|---|---|---|---|
| 28548.0 | 0.454 | 0.291 | 0.301 | 0.386 |

| country | s1_name | s1_address | target_name | target_address |
|---|---|---|---|---|
| India | Lotus Properties Limited | Flat No. 1504, 15Th Floor, A-2 Clover Wing, Mohan Pride, Next To Amrut Park, Kalyan, Thane, Maharashtra | लोटस प्रॉपर्टीज लिमिटेड | #4504, KALYAN, THANE, Maharashtra |
| India | Ram Investments Private Limited | Flat No. 612, 6Th Floor, Shree Sainath Chs Ltd, Kaatyayni Heights, Near Sona Udyog, Andh, Eri East, Mumbai, Mumbai City, Maharashtra | राम इन्वेस्टमेंट्स प्राइवेट लिमिटेड | FLAT NO. 612, MUMBAI, Maharashtra |
| India | Shree Global Private Limited | Pl -35, S No 24 25 Shikshak Nagar Wanwadi, Pune, Maharashtra, Pune | श्री ग्लोबल प्राइवेट लिमिटेड | PUNE, PL -3-5, PUNE, Maharashtra |
| India | Kms International Private Limited | Atno.17, Casa Capitol, 3Rd Floor, Wood Street, Ashoknagar, Bangalore, Karnataka | kmsinternational.com | Atno.17, Bangalore, ಕರ್ನಾಟಕ |
| US | Montium Electricity L.L.C. | 4017 Broadway Avenue, Unit APT B, Evansville, IN | MONTIUM L.L.C. [CENTER] | None |
| India | Indian Food Private Limited | O-9, Sector-3, Dsiidc, Bawana, New Delhi, Delhi | इंडियन फूड प्राइवेट लिमिटेड | O-C-9, NEW DELHI, Delhi |
| US | Kaufman Parts LLC | 30546 Lowell Road, Albemarle, NC | kaufmanparts.c0m | ALBEMARLE, NC, 030546 Lowell Road |
| India | Balaji Consulting Private Limited | 313/73 Anand Nagarinderlok, Delhi, North Delhi, Delhi | Rizaquo | No D/313/73 Anand Nagarinderlok, North Delhi, Delhi, DL |
| India | Perfect Foundation Private Limited | 2690/1, Beadon Pura, Karol Bagh, New Delhi, New Delhi, Central Delhi, Delhi | परफेक्ट फाउंडेशन प्राइवेट लिमिटेड | 2690/1, NEW DELHI, CENTRAL DELHI, Delhi |
| US | United Pediatrics LLC | 12736 200, Mahnomen, MN | United Pmbedatgcs  LLC | 12736 200, PMB 8763, MAHNOEN, MN |
| India | Bright Consultancy Private Limited | 18/223, Mannuthy, Nadathara Road, Thrissur, Kerala | ബ്രൈറ്റ് കൺസൾട്ടൻസി പ്രൈവറ്റ് ലിമിറ്റഡ് | 8/223, Mannuthy, Nadathara Road, Thrissur, KL |
| US | Dotty Lucero West LLC | 2849 Stephanie Lane, Hurst, TX | Dotty Lucero LLC Center | None |
