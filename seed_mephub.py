"""MEPhub demo seeder: WIPES all marketplace data, then loads a realistic MEP catalogue.

    export SEED_ADMIN_PASSWORD='choose-a-strong-one'
    export SEED_USER_PASSWORD='choose-another'
    python seed_mephub.py --yes

All part numbers, prices and stock levels are DEMO data (not real quotations).
Passwords come from the environment so they are never committed to Git.
"""
import os
import sys
from datetime import date, timedelta, datetime, timezone

from sqlalchemy import text

from app import create_app
from app.models import Users, Sellers, Categories, Products, PriceTiers, Addresses, Orders
from app.services import order_service
from app.utils import db

ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD")
USER_PASSWORD = os.getenv("SEED_USER_PASSWORD")

# ---------------------------------------------------------------- accounts --
ADMIN = ("admin@mephub.id", "MEPhub Admin")
BUYERS = [
    ("buyer@mephub.id", "Budi Santoso"),
    ("kontraktor@mephub.id", "Rudi Hartono (PT Karya Konstruksi)"),
    ("e2e.buyer@mephub.id", "E2E Test Buyer"),
]
SUPPLIERS = {
    "ape": ("ape@mephub.id", "PT Angkasa Panelindo Elektrik", "Electrical panels, protection and motor control for projects across West Java."),
    "mek": ("mekanikal@mephub.id", "Bandung Mekanikal Utama", "Bearings, transmission parts and pneumatics for factories and workshops."),
    "aqua": ("aqua@mephub.id", "Aqua Pipa Nusantara", "PPR/PVC pipes, valves and pumps for buildings and plumbing contractors."),
    "safe": ("safety@mephub.id", "Safetyline Industrial Supply", "PPE and measuring tools for industrial sites."),
}

# -------------------------------------------------------------- categories --
CATEGORY_TREE = {
    "Electrical": ["Circuit Protection", "Motor Control", "Control & Signalling", "Cables & Accessories", "Panel & Enclosures"],
    "Mechanical": ["Bearings & Transmission", "Pneumatics"],
    "Plumbing": ["Pipes & Fittings", "Valves & Pumps"],
    "Safety & Tools": ["PPE", "Measuring Tools"],
}

# ---------------------------------------------------------------- products --
# (supplier, category, name, sku, brand, price, stock, unit, moq, tkdn, ("stock"|lead_days), tiers, intro, specs)
P = []


def add(sup, cat, name, sku, brand, price, stock, unit="pcs", moq=1, tkdn=None, lead=None, tiers=(), intro="", **specs):
    P.append((sup, cat, name, sku, brand, price, stock, unit, moq, tkdn, lead, list(tiers), intro, specs))


# Circuit Protection
add("ape", "Circuit Protection", "MCB 1P 10A 6kA C-Curve", "EZ9F34110", "Schneider Electric", 62000, 480, tkdn=38.5,
    tiers=[(12, 56000), (48, 50000)], intro="Miniature circuit breaker for lighting and small power circuits.",
    **{"Poles": "1P", "Rated current": "10 A", "Breaking capacity": "6 kA", "Curve": "C", "Mounting": "DIN rail"})
add("ape", "Circuit Protection", "MCB 3P 32A 6kA C-Curve", "EZ9F34332", "Schneider Electric", 385000, 160, tkdn=38.5,
    tiers=[(6, 360000)], intro="Three-pole MCB for motor feeders and sub-distribution.",
    **{"Poles": "3P", "Rated current": "32 A", "Breaking capacity": "6 kA", "Curve": "C"})
add("ape", "Circuit Protection", "MCB 2P 20A 4.5kA C-Curve", "A9K24220", "Schneider Electric", 148000, 220, tkdn=35.0,
    tiers=[(10, 138000)], **{"Poles": "2P", "Rated current": "20 A", "Breaking capacity": "4.5 kA"})
add("ape", "Circuit Protection", "RCBO 1P+N 16A 30mA", "DOMD01616", "Schneider Electric", 399000, 75,
    intro="Combined overcurrent and earth-leakage protection.", **{"Poles": "1P+N", "Rated current": "16 A", "Sensitivity": "30 mA"})
add("ape", "Circuit Protection", "MCCB 3P 100A 25kA", "NXM-100S/3P", "CHINT", 1450000, 14, tkdn=40.2,
    tiers=[(5, 1380000)], intro="Moulded case circuit breaker, thermal-magnetic.",
    **{"Poles": "3P", "Rated current": "100 A", "Breaking capacity": "25 kA", "Voltage": "380/415 VAC"})
add("ape", "Circuit Protection", "MCCB 3P 400A 36kA", "ABN403C-400", "LS Electric", 6850000, 0, lead=14,
    intro="Made to order. Ships from the distributor after confirmation.",
    **{"Poles": "3P", "Rated current": "400 A", "Breaking capacity": "36 kA"})
add("ape", "Circuit Protection", "ACB 1000A 3P 50kA", "MVS10N3MD2A", "Schneider Electric", 31546000, 0, tkdn=26.89, lead=28,
    intro="Air circuit breaker for main distribution boards.", **{"Poles": "3P", "Rated current": "1000 A", "Breaking capacity": "50 kA"})
# Motor Control
add("ape", "Motor Control", "Contactor 3P 9A 220VAC Coil", "LC1E0910M5", "Schneider Electric", 285000, 120, tkdn=30.0,
    tiers=[(10, 262000)], **{"Rated current (AC-3)": "9 A", "Power (400V)": "4 kW", "Coil voltage": "220 VAC", "Contacts": "1NO"})
add("ape", "Motor Control", "Contactor 3P 25A 220VAC Coil", "LC1E2510M5", "Schneider Electric", 612000, 64, tkdn=30.0,
    tiers=[(5, 575000)], **{"Rated current (AC-3)": "25 A", "Power (400V)": "11 kW", "Coil voltage": "220 VAC"})
add("ape", "Motor Control", "Thermal Overload Relay 4-6A", "LRE10", "Schneider Electric", 272000, 90,
    tiers=[(10, 250000)], **{"Setting range": "4-6 A", "Class": "10A", "Reset": "Manual/Auto"})
add("ape", "Motor Control", "Motor Circuit Breaker 6-10A", "GV2ME14", "Schneider Electric", 735000, 40, **{"Setting range": "6-10 A", "Breaking capacity": "100 kA @ 400V"})
add("ape", "Motor Control", "Soft Starter 15kW 400V", "ATS22D32Q", "Schneider Electric", 12850000, 0, lead=21,
    intro="Made to order.", **{"Power": "15 kW", "Voltage": "400 VAC", "Control": "Torque control"})
# Control & Signalling
add("ape", "Control & Signalling", "Push Button 22mm Green Flush", "XB4BA31", "Schneider Electric", 118000, 150, moq=2,
    tiers=[(20, 99000)], **{"Diameter": "22 mm", "Contacts": "1NO", "Colour": "Green"})
add("ape", "Control & Signalling", "Pilot Lamp 22mm LED 220VAC Red", "XB7EV04MP", "Schneider Electric", 45177, 300, moq=2,
    tiers=[(10, 41500), (50, 38000)], **{"Diameter": "22 mm", "Voltage": "220 VAC", "Colour": "Red", "Type": "LED"})
add("ape", "Control & Signalling", "Emergency Stop 22mm Mushroom", "XB4BS8442", "Schneider Electric", 210000, 55, **{"Diameter": "22 mm", "Head": "40 mm mushroom", "Release": "Turn to release"})
add("ape", "Control & Signalling", "Selector Switch 22mm 3-Position", "XB5AD33", "Schneider Electric", 196000, 48, **{"Diameter": "22 mm", "Positions": "3", "Contacts": "2NO"})
add("ape", "Control & Signalling", "Plug-in Relay 24VDC 8-Pin", "RXM2AB2BD", "Schneider Electric", 96000, 140, tiers=[(10, 88000)], **{"Coil": "24 VDC", "Contacts": "2 C/O", "Rated current": "12 A"})
# Cables & Accessories
add("ape", "Cables & Accessories", "NYM Cable 3x2.5mm2 (Roll 50m)", "NYM-3X25-50", "Supreme", 1085000, 36, unit="roll", tkdn=60.0,
    tiers=[(5, 1040000), (20, 995000)], intro="PVC-insulated sheathed cable for fixed installation.",
    **{"Cores": "3", "Cross-section": "2.5 mm2", "Length": "50 m", "Standard": "SNI"})
add("ape", "Cables & Accessories", "NYAF Cable 1x1.5mm2 Red (Roll 100m)", "NYAF-1X15-RD", "Kabelindo", 395000, 80, unit="roll", tkdn=60.0,
    tiers=[(5, 372000)], **{"Cores": "1", "Cross-section": "1.5 mm2", "Length": "100 m", "Colour": "Red"})
add("ape", "Cables & Accessories", "Cable Lug Ring 10mm2 (Pack 100)", "SKUN-R10-100", "Generic", 165000, 200, unit="pack", moq=2, tiers=[(10, 148000)],
    **{"Size": "10 mm2", "Type": "Ring, insulated", "Pack": "100 pcs"})
add("ape", "Cables & Accessories", "Cable Tie 200mm Black (Pack 100)", "CT-200-BK", "Generic", 24000, 500, unit="pack", moq=5,
    tiers=[(20, 21000), (100, 18500)], **{"Length": "200 mm", "Width": "3.6 mm", "Material": "Nylon 66"})
add("ape", "Cables & Accessories", "Cable Duct 40x60mm 2m", "DUCT-4060-2M", "Generic", 58000, 260, tiers=[(20, 53000)], **{"Size": "40 x 60 mm", "Length": "2 m", "Material": "PVC"})
# Panel & Enclosures
add("ape", "Panel & Enclosures", "Wall-mount Enclosure 400x300x200 IP65", "ENC-403020", "Himel", 1285000, 22, tiers=[(5, 1190000)],
    **{"Size": "400 x 300 x 200 mm", "Ingress protection": "IP65", "Material": "Steel, powder-coated"})
add("ape", "Panel & Enclosures", "MCB Box 12 Module Flush", "DOMH12112F", "Schneider Electric", 190967, 60, **{"Modules": "12", "Mounting": "Flush", "Door": "Transparent"})
add("ape", "Panel & Enclosures", "Copper Busbar 3x20mm (per metre)", "BB-CU-3X20", "Generic", 265000, 140, unit="m", moq=5, tiers=[(20, 248000)],
    **{"Cross-section": "3 x 20 mm", "Material": "Electrolytic copper", "Rated current": "~150 A"})
add("ape", "Panel & Enclosures", "Main Distribution Panel 400A (Custom)", "MDP-400-CUSTOM", "PT APE", 48500000, 0, lead=35,
    intro="Fabricated to your single-line diagram. Send an RFQ-style PO note with the SLD reference.",
    **{"Rated current": "400 A", "Form": "Form 2b", "Finish": "Powder coat RAL 7035"})
# Bearings & Transmission
add("mek", "Bearings & Transmission", "Deep Groove Ball Bearing 6205-2RS", "6205-2RS", "SKF", 78000, 400, moq=2, tiers=[(10, 71000), (50, 64000)],
    **{"Bore": "25 mm", "Outer diameter": "52 mm", "Width": "15 mm", "Seal": "Rubber, both sides"})
add("mek", "Bearings & Transmission", "Deep Groove Ball Bearing 6308-ZZ", "6308-ZZ", "NSK", 142000, 180, moq=2, tiers=[(10, 131000)],
    **{"Bore": "40 mm", "Outer diameter": "90 mm", "Width": "23 mm", "Seal": "Metal shield"})
add("mek", "Bearings & Transmission", "V-Belt B-52", "VB-B52", "Mitsuboshi", 61000, 150, tiers=[(10, 55000)], **{"Section": "B", "Length": "52 in"})
add("mek", "Bearings & Transmission", "Roller Chain 08B-1 (Box 5m)", "RC-08B1-5M", "DID", 395000, 45, unit="box", **{"Pitch": "12.7 mm", "Length": "5 m"})
add("mek", "Bearings & Transmission", "Flexible Jaw Coupling L-095", "CPL-L095", "Generic", 215000, 70, tiers=[(5, 198000)], **{"Type": "Jaw", "Max bore": "28 mm"})
# Pneumatics
add("mek", "Pneumatics", "Pneumatic Cylinder 50x100 ISO 15552", "PC-50-100", "Airtac", 785000, 26, **{"Bore": "50 mm", "Stroke": "100 mm", "Pressure": "1-10 bar"})
add("mek", "Pneumatics", "Solenoid Valve 5/2 24VDC", "SV-52-24D", "Airtac", 345000, 58, tiers=[(5, 318000)], **{"Ports": "5/2", "Coil": "24 VDC", "Thread": "G1/4"})
add("mek", "Pneumatics", "PU Tube 8mm (Roll 100m)", "PU-8-100", "Generic", 520000, 34, unit="roll", tiers=[(5, 485000)], **{"Outer diameter": "8 mm", "Material": "Polyurethane"})
add("mek", "Pneumatics", "Air Filter Regulator 1/4in", "AFR-2000", "Airtac", 295000, 40, **{"Thread": "G1/4", "Max pressure": "10 bar"})
add("mek", "Pneumatics", "Push-in Fitting 8mm x G1/4 (Pack 10)", "PF-8-14-10", "Generic", 98000, 120, unit="pack", moq=2, tiers=[(10, 88000)], **{"Tube": "8 mm", "Thread": "G1/4"})
# Pipes & Fittings
add("aqua", "Pipes & Fittings", "PPR Pipe PN-20 25mm (4m)", "PPR-PN20-25", "Rucika", 68000, 600, unit="batang", moq=4, tkdn=55.0,
    tiers=[(40, 62000), (200, 57000)], **{"Diameter": "25 mm", "Pressure rating": "PN-20", "Length": "4 m", "Use": "Hot and cold water"})
add("aqua", "Pipes & Fittings", "PPR Pipe PN-10 32mm (4m)", "PPR-PN10-32", "Rucika", 74000, 420, unit="batang", moq=4, tkdn=55.0,
    tiers=[(40, 68000)], **{"Diameter": "32 mm", "Pressure rating": "PN-10", "Length": "4 m"})
add("aqua", "Pipes & Fittings", "PPR Elbow 90deg 25mm (Pack 20)", "PPR-EL90-25", "Rucika", 128000, 200, unit="pack", tiers=[(10, 118000)], **{"Diameter": "25 mm", "Angle": "90 deg"})
add("aqua", "Pipes & Fittings", "PVC Pipe AW 3in (4m)", "PVC-AW-3", "Wavin", 112000, 300, unit="batang", moq=2, tiers=[(20, 104000)], **{"Diameter": "3 in", "Class": "AW", "Length": "4 m"})
add("aqua", "Pipes & Fittings", "PVC Solvent Cement 500g", "PVC-GLUE-500", "Aica", 54000, 180, tiers=[(12, 49000)], **{"Content": "500 g"})
# Valves & Pumps
add("aqua", "Valves & Pumps", "Brass Ball Valve 1/2in", "BV-BR-12", "Onda", 48000, 350, moq=2, tiers=[(24, 43000)], **{"Size": "1/2 in", "Material": "Brass", "Pressure": "PN-16"})
add("aqua", "Valves & Pumps", "Bronze Gate Valve 2in", "GV-BZ-2", "Kitz", 485000, 38, **{"Size": "2 in", "Material": "Bronze"})
add("aqua", "Valves & Pumps", "Swing Check Valve 1in", "CV-BR-1", "Onda", 89000, 110, tiers=[(10, 81000)], **{"Size": "1 in", "Type": "Swing"})
add("aqua", "Valves & Pumps", "Shallow Well Pump 125W", "PS-130BIT", "Shimizu", 765000, 9, **{"Power": "125 W", "Max head": "33 m", "Suction": "9 m"})
add("aqua", "Valves & Pumps", "Water Meter 1/2in Class B", "WM-12-B", "Itron", 215000, 75, tiers=[(10, 198000)], **{"Size": "1/2 in", "Class": "B"})
# PPE
add("safe", "PPE", "Safety Shoes Steel Toe Size 42", "SH-ST-42", "Safety Jogger", 565000, 30, tiers=[(6, 525000)], **{"Toe cap": "Steel", "Sole": "Oil-resistant"})
add("safe", "PPE", "Safety Helmet with Chin Strap", "HLM-ABS-Y", "Generic", 45000, 220, moq=5, tiers=[(50, 39000)], **{"Material": "ABS", "Colour": "Yellow"})
add("safe", "PPE", "Cut-Resistant Gloves Level 5 (Pair)", "GLV-CR5", "Generic", 62000, 260, unit="pair", moq=6, tiers=[(24, 55000), (120, 49000)], **{"Cut level": "5", "Coating": "PU"})
add("safe", "PPE", "Insulated Gloves Class 0 1000V", "GLV-INS-C0", "Salisbury", 1850000, 0, unit="pair", lead=10, intro="Made to order.", **{"Class": "0", "Test voltage": "5 kV AC"})
add("safe", "PPE", "Safety Glasses Clear Anti-Fog", "SG-CLR-AF", "Generic", 28000, 300, moq=5, tiers=[(50, 24000)], **{"Lens": "Polycarbonate", "Coating": "Anti-fog"})
# Measuring Tools
add("safe", "Measuring Tools", "AC Clamp Meter 600A", "FLK-117-CM", "Fluke", 3250000, 12, tkdn=None, **{"Range": "600 A AC", "Display": "True RMS"})
add("safe", "Measuring Tools", "Insulation Resistance Tester 1000V", "IRT-1000", "Kyoritsu", 4850000, 6, **{"Test voltage": "1000 V", "Range": "up to 4000 MOhm"})
add("safe", "Measuring Tools", "Digital Multimeter CAT III", "DMM-CAT3", "Fluke", 1450000, 25, **{"Category": "CAT III 600V", "Display": "True RMS"})
add("safe", "Measuring Tools", "Laser Distance Meter 50m", "LDM-50", "Bosch", 1250000, 18, **{"Range": "50 m", "Accuracy": "+/- 2 mm"})

BG = {"Electrical": "0f4c81", "Mechanical": "5b3a29", "Plumbing": "0b6e6e", "Safety & Tools": "9a3412"}


def build_description(intro, specs):
    lines = [f"{k}: {v}" for k, v in specs.items()]
    return (intro + "\n\n" if intro else "") + "\n".join(lines)


def wipe():
    """Empty every marketplace table (alembic_version is NOT touched)."""
    names = ", ".join(f'"{t.name}"' for t in db.metadata.sorted_tables)
    if db.engine.dialect.name == "postgresql":
        db.session.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))
    else:
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
    db.session.commit()


def make_user(email, name, password, role="user"):
    user = Users(email=email, full_name=name, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    return user


def seed():
    admin = make_user(*ADMIN, ADMIN_PASSWORD, role="admin")
    buyers = {email: make_user(email, name, USER_PASSWORD) for email, name in BUYERS}
    sellers = {}
    for key, (email, store, about) in SUPPLIERS.items():
        user = make_user(email, store, USER_PASSWORD)
        db.session.add(Sellers(id=user.id, store_name=store, store_description=about))
        sellers[key] = user.id

    leaf_ids = {}
    for parent_name, children in CATEGORY_TREE.items():
        parent = Categories(name=parent_name, description=f"{parent_name} products for MEP projects")
        db.session.add(parent)
        db.session.flush()
        for child in children:
            leaf = Categories(name=child, parent_id=parent.id)
            db.session.add(leaf)
            db.session.flush()
            leaf_ids[child] = (leaf.id, parent_name)

    for i, (sup, cat, name, sku, brand, price, stock, unit, moq, tkdn, lead, tiers, intro, specs) in enumerate(P, 1):
        cat_id, root = leaf_ids[cat]
        product = Products(
            category_id=cat_id, seller_id=sellers[sup], name=name, slug=f"{sku.lower()}-{i:03d}", sku=sku, brand=brand,
            price=price, stock=stock, unit=unit, min_order_qty=moq, tkdn_percent=tkdn,
            datasheet_url=f"https://example.com/datasheets/{sku}.pdf",
            fulfillment_type="indent" if lead else "stock", lead_time_days=lead,
            description=build_description(intro, specs),
            image_url=f"https://dummyimage.com/600x600/{BG[root]}/ffffff.png&text={sku}",
        )
        db.session.add(product)
        db.session.flush()
        for min_qty, tier_price in tiers:
            db.session.add(PriceTiers(product_id=product.id, min_qty=min_qty, unit_price=tier_price))
    db.session.commit()

    # saved addresses
    def addr(user, label, recipient, phone, line, city, prov, postal, default=False):
        db.session.add(Addresses(user_id=user.id, label=label, recipient_name=recipient, phone=phone,
                                 address_line=line, city=city, province=prov, postal_code=postal, is_default=default))

    b, k, e = buyers["buyer@mephub.id"], buyers["kontraktor@mephub.id"], buyers["e2e.buyer@mephub.id"]
    addr(b, "Workshop", "Budi Santoso", "081234567801", "Jl. Soekarno-Hatta No. 120", "Bandung", "Jawa Barat", "40286", True)
    addr(b, "Project Site Cimahi", "Pak Asep", "081234567802", "Jl. Industri Raya Blok C-4, Cimahi", "Cimahi", "Jawa Barat", "40513")
    addr(k, "Gedung DPRD (Site)", "Rudi Hartono", "081234567803", "Jl. Pejanggik No. 12", "Mataram", "Nusa Tenggara Barat", "83121", True)
    addr(k, "Office", "Rudi Hartono", "081234567804", "Jl. Asia Afrika No. 55", "Bandung", "Jawa Barat", "40111")
    addr(e, "E2E Address", "E2E Test Buyer", "081200000000", "Jl. Testing No. 1", "Bandung", "Jawa Barat", "40111", True)
    db.session.commit()

    # ---- demo orders, created through the real order engine -------------------
    by_sku = {p.sku: p for p in Products.query.all()}
    pid = lambda sku: by_sku[sku].id
    plan = [
        # (buyer, items, kwargs, final_status, payment_status, days_ago)
        (b, [("EZ9F34110", 24), ("NYM-3X25-50", 6)], dict(po_number="PO-BS-0001", notes="Kirim sebelum jam 15.00"), "delivered", "paid", 40),
        (b, [("6205-2RS", 20), ("VB-B52", 4)], dict(po_number="PO-BS-0002"), "shipped", "paid", 9),
        (b, [("LC1E0910M5", 10), ("LRE10", 10)], dict(payment_method="request_terms", po_number="PO-BS-0003"), "processing", "terms_approved", 5),
        (b, [("EZ9F34110", 12), ("HLM-ABS-Y", 10)], dict(po_number="PO-BS-0004"), "pending", "unpaid", 1),
        (k, [("NXM-100S/3P", 6), ("ENC-403020", 6)], dict(po_number="PO-KK-DPRD-01", notes="Untuk panel lantai 2"), "delivered", "paid", 33),
        (k, [("PPR-PN20-25", 80), ("BV-BR-12", 24)], dict(po_number="PO-KK-DPRD-02"), "shipped", "paid", 12),
        (k, [("XB7EV04MP", 50), ("XB4BA31", 20)], dict(payment_method="request_terms", po_number="PO-KK-DPRD-03"), "processing", "terms_approved", 6),
        (k, [("MDP-400-CUSTOM", 1)], dict(payment_method="request_terms", po_number="PO-KK-DPRD-04", notes="Sesuai SLD Rev.B"), "pending", "terms_requested", 2),
        (k, [("GLV-CR5", 24)], dict(), "cancelled", "unpaid", 20),
        (e, [("SG-CLR-AF", 5)], dict(), "pending", "unpaid", 1),
    ]
    for user, items, extra, status, pay_status, days_ago in plan:
        payload = {"items": [{"product_id": pid(s), "quantity": q} for s, q in items], "shipping_address": "Jl. Demo No. 1, Bandung", **extra}
        if "payment_method" not in payload:
            payload["payment_method"] = "bank_transfer"
        orders, error = order_service.create_order(user.id, payload)
        if error:
            raise SystemExit(f"Seed order failed: {error}")
        when = datetime.now(timezone.utc) - timedelta(days=days_ago)
        for order in orders:
            order.status, order.payment_status, order.created_at = status, pay_status, when
            if status == "cancelled":  # give the stock back like a real cancellation would
                for item in order.order_items:
                    if item.product.fulfillment_type == "stock":
                        item.product.stock += item.quantity
        db.session.commit()


def main():
    if "--yes" not in sys.argv and os.getenv("CONFIRM_RESET") != "yes":
        raise SystemExit("This WIPES all data. Re-run with:  python seed_mephub.py --yes")
    if not ADMIN_PASSWORD or not USER_PASSWORD:
        raise SystemExit("Set SEED_ADMIN_PASSWORD and SEED_USER_PASSWORD first (they are not stored in Git).")
    app = create_app()
    with app.app_context():
        host = db.engine.url.host
        print(f"Resetting database on host: {host}")
        wipe()
        seed()
        print(f"Seeded: {Users.query.count()} users, {Sellers.query.count()} suppliers, "
              f"{Categories.query.count()} categories, {Products.query.count()} products, {Orders.query.count()} orders.")
        print("Admin   :", ADMIN[0])
        print("Buyers  :", ", ".join(email for email, _ in BUYERS))
        print("Suppliers:", ", ".join(v[0] for v in SUPPLIERS.values()))


if __name__ == "__main__":
    main()