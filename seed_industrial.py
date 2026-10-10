"""
Industrial catalog seeder for MEPhub Industrial.

Turns the demo marketplace into a B2B catalog for industrial & manufacturing goods:
  - adds industrial category hierarchies and fictional demo suppliers
  - adds ~20 industrial products whose descriptions use "Key: Value" lines
    (Brand, Part No, specs, Unit, Min. order) that the frontend renders as a spec table
  - deactivates (soft-deletes) the non-industrial demo products from seed.py
  - creates ONE demo buyer with a few orders, used by the frontend's /orders page

It is idempotent: safe to run more than once. It never hard-deletes anything.

Usage (the password comes from the environment, never from the code):
    DEMO_BUYER_PASSWORD="choose-a-password" python seed_industrial.py
    DATABASE_URL="<DATABASE_PUBLIC_URL from Railway>" DEMO_BUYER_PASSWORD="..." python seed_industrial.py
"""
import os
import secrets
import sys

from sqlalchemy.exc import IntegrityError

from app import create_app
from app.models import Users, Sellers, Categories, Products, Orders, OrderItems
from app.services.product_service import generate_unique_slug
from app.utils import db

app = create_app()

DEMO_BUYER_EMAIL = "demo.buyer@revoshop.demo"
DEMO_BUYER_NAME = "Demo Procurement Buyer"

# Stores created by seed.py that do not fit an industrial marketplace
LEGACY_STORES = ["Mianis Cubes", "OfficeMart Bandung", "Locust Mega Store"]

# (name, description, parent name or None)
CATEGORIES = [
    ("Mechanical & Power Transmission", "Bearings, belts, chains and couplings for rotating equipment.", None),
    ("Bearings & Seals", "Ball, roller and tapered bearings.", "Mechanical & Power Transmission"),
    ("Belts, Chains & Couplings", "Drive belts, roller chains and shaft couplings.", "Mechanical & Power Transmission"),
    ("Automation & Control", "Sensors, contactors and control components.", None),
    ("Sensors & Switches", "Proximity, photoelectric and limit switches.", "Automation & Control"),
    ("Contactors & Relays", "Power contactors and control relays.", "Automation & Control"),
    ("Pneumatics & Hydraulics", "Actuators, valves, tubing and fittings.", None),
    ("Pneumatic Cylinders & Valves", "Cylinders and solenoid valves.", "Pneumatics & Hydraulics"),
    ("Hoses & Fittings", "Tubing, hoses and push-in fittings.", "Pneumatics & Hydraulics"),
    ("Safety & PPE", "Personal protective equipment for plant and workshop use.", None),
    ("Head & Eye Protection", "Helmets, goggles and face shields.", "Safety & PPE"),
    ("Gloves & Protective Wear", "Work gloves and protective clothing.", "Safety & PPE"),
    ("Tools & Instruments", "Hand tools and measuring instruments.", None),
    ("Hand & Power Tools", "Torque tools and power tools.", "Tools & Instruments"),
    ("Measuring Instruments", "Calipers, multimeters and gauges.", "Tools & Instruments"),
]

# (store name, owner email, owner full name, store description)
NEW_SUPPLIERS = [
    ("Bandung Bearing & Transmission", "supplier.bearing@revoshop.demo", "Bearing Supplier",
     "Demo supplier of bearings, belts, chains and couplings."),
    ("Pneumatik Nusantara", "supplier.pneumatic@revoshop.demo", "Pneumatic Supplier",
     "Demo supplier of pneumatic cylinders, valves and fittings."),
    ("Safetyline Industrial Supply", "supplier.safety@revoshop.demo", "Safety Supplier",
     "Demo supplier of industrial safety equipment."),
    ("Presisi Instrument Co.", "supplier.instrument@revoshop.demo", "Instrument Supplier",
     "Demo supplier of measuring instruments, sensors and tools."),
]

ANGKASA = "PT Angkasa Panelindo Elektrik"


def img(bg, text):
    return f"https://dummyimage.com/400x400/{bg}/f9fafb&text={text.replace(' ', '+')}"


def spec(*lines):
    return "\n".join(lines)


# (supplier store, category, name, price IDR, stock, image, description)
PRODUCTS = [
    # --- PT Angkasa Panelindo Elektrik (new items) ---
    (ANGKASA, "Circuit Breakers & MCBs", "MCCB 3P 100A 25kA", 1450000, 14, img("1f2937", "MCCB 3P 100A"),
     spec("Brand: PanelPro", "Part No: MCCB-3P-100-25", "Rating: 3 pole, 100 A, 25 kA breaking capacity",
          "Mounting: Fixed, panel mount", "Unit: pcs", "Min. order: 1 pcs")),
    (ANGKASA, "Contactors & Relays", "Contactor 9A 3P 24VAC Coil", 285000, 40, img("1f2937", "Contactor 9A"),
     spec("Brand: PanelPro", "Part No: CTR-9-3P-24", "Rating: 9 A AC-3, 3 pole", "Coil: 24 VAC",
          "Unit: pcs", "Min. order: 1 pcs")),
    # --- Bandung Bearing & Transmission ---
    ("Bandung Bearing & Transmission", "Bearings & Seals", "Deep Groove Ball Bearing 6204-2RS", 38000, 320,
     img("334155", "Bearing 6204"),
     spec("Brand: TransDrive", "Part No: BRG-6204-2RS", "Size: 20 x 47 x 14 mm (bore x OD x width)",
          "Seal: Rubber, both sides", "Unit: pcs", "Min. order: 10 pcs")),
    ("Bandung Bearing & Transmission", "Bearings & Seals", "Tapered Roller Bearing 30205", 85000, 120,
     img("334155", "Bearing 30205"),
     spec("Brand: TransDrive", "Part No: BRG-30205", "Size: 25 x 52 x 16.25 mm", "Type: Single row tapered",
          "Unit: pcs", "Min. order: 4 pcs")),
    ("Bandung Bearing & Transmission", "Belts, Chains & Couplings", "V-Belt B-52", 48000, 90,
     img("334155", "V-Belt B-52"),
     spec("Brand: TransDrive", "Part No: VB-B52", "Profile: B section, 52 in inside length",
          "Material: Rubber, oil resistant", "Unit: pcs", "Min. order: 2 pcs")),
    ("Bandung Bearing & Transmission", "Belts, Chains & Couplings", "Roller Chain 08B-1 (per meter)", 95000, 400,
     img("334155", "Roller Chain 08B"),
     spec("Brand: TransDrive", "Part No: CHN-08B-1", "Pitch: 12.7 mm, single strand", "Material: Carbon steel",
          "Unit: meter", "Min. order: 5 meter")),
    ("Bandung Bearing & Transmission", "Belts, Chains & Couplings", "Jaw Coupling GR28 with Spider", 135000, 36,
     img("334155", "Jaw Coupling GR28"),
     spec("Brand: TransDrive", "Part No: CPL-GR28", "Max bore: 28 mm", "Spider: Polyurethane 92 Shore A",
          "Unit: set", "Min. order: 1 set")),
    # --- Pneumatik Nusantara ---
    ("Pneumatik Nusantara", "Pneumatic Cylinders & Valves", "Double-Acting Pneumatic Cylinder 32 x 100 mm", 320000, 22,
     img("0f766e", "Cylinder 32x100"),
     spec("Brand: AeroFlow", "Part No: CYL-DA-32-100", "Bore / stroke: 32 mm / 100 mm", "Operating pressure: 1 - 10 bar",
          "Unit: pcs", "Min. order: 1 pcs")),
    ("Pneumatik Nusantara", "Pneumatic Cylinders & Valves", "5/2 Solenoid Valve 1/4 in 24VDC", 275000, 4,
     img("0f766e", "Solenoid Valve 5-2"),
     spec("Brand: AeroFlow", "Part No: VLV-52-14-24DC", "Function: 5/2 single solenoid, spring return",
          "Port: G1/4", "Coil: 24 VDC", "Unit: pcs", "Min. order: 1 pcs")),
    ("Pneumatik Nusantara", "Hoses & Fittings", "PU Pneumatic Tube 8 mm (100 m roll)", 420000, 15,
     img("0f766e", "PU Tube 8mm"),
     spec("Brand: AeroFlow", "Part No: TUB-PU-8-100", "Size: 8 mm OD x 5 mm ID", "Material: Polyurethane",
          "Unit: roll (100 m)", "Min. order: 1 roll")),
    ("Pneumatik Nusantara", "Hoses & Fittings", "Push-in Fitting Straight 8 mm - 1/4 in (pack of 10)", 85000, 60,
     img("0f766e", "Push-in Fitting"),
     spec("Brand: AeroFlow", "Part No: FIT-PI-8-14", "Tube: 8 mm, thread G1/4", "Material: Nickel-plated brass",
          "Unit: pack (10 pcs)", "Min. order: 1 pack")),
    # --- Safetyline Industrial Supply ---
    ("Safetyline Industrial Supply", "Head & Eye Protection", "Safety Helmet ABS with Ratchet Suspension", 55000, 150,
     img("b45309", "Safety Helmet"),
     spec("Brand: SafeGuard", "Part No: HLM-ABS-R", "Material: ABS shell", "Adjustment: 6-point ratchet",
          "Unit: pcs", "Min. order: 5 pcs")),
    ("Safetyline Industrial Supply", "Head & Eye Protection", "Safety Goggles Anti-Fog Clear", 32000, 210,
     img("b45309", "Safety Goggles"),
     spec("Brand: SafeGuard", "Part No: GOG-AF-CLR", "Lens: Polycarbonate, anti-fog, UV protection",
          "Unit: pcs", "Min. order: 10 pcs")),
    ("Safetyline Industrial Supply", "Gloves & Protective Wear", "Nitrile-Coated Work Gloves Size L (pair)", 28000, 480,
     img("b45309", "Work Gloves"),
     spec("Brand: SafeGuard", "Part No: GLV-NIT-L", "Coating: Nitrile palm", "Size: L", "Unit: pair",
          "Min. order: 12 pair")),
    ("Safetyline Industrial Supply", "Gloves & Protective Wear", "Welding Gloves Leather 14 in (pair)", 95000, 0,
     img("b45309", "Welding Gloves"),
     spec("Brand: SafeGuard", "Part No: GLV-WLD-14", "Material: Split cowhide leather", "Length: 14 in",
          "Unit: pair", "Min. order: 2 pair")),
    # --- Presisi Instrument Co. ---
    ("Presisi Instrument Co.", "Measuring Instruments", "Digital Vernier Caliper 0-150 mm", 285000, 45,
     img("4338ca", "Digital Caliper"),
     spec("Brand: Presita", "Part No: CAL-D-150", "Range: 0 - 150 mm", "Resolution: 0.01 mm",
          "Unit: pcs", "Min. order: 1 pcs")),
    ("Presisi Instrument Co.", "Measuring Instruments", "Digital Multimeter True RMS CAT III 600V", 850000, 18,
     img("4338ca", "Multimeter True RMS"),
     spec("Brand: Presita", "Part No: DMM-TRMS-600", "Measurement: AC/DC V, A, resistance, capacitance",
          "Safety rating: CAT III 600 V", "Unit: pcs", "Min. order: 1 pcs")),
    ("Presisi Instrument Co.", "Hand & Power Tools", "Torque Wrench 1/2 in Drive 40-200 Nm", 1250000, 0,
     img("4338ca", "Torque Wrench"),
     spec("Brand: TorqPro", "Part No: TW-12-200", "Drive: 1/2 in square", "Range: 40 - 200 Nm",
          "Accuracy: +/- 4%", "Unit: pcs", "Min. order: 1 pcs")),
    ("Presisi Instrument Co.", "Hand & Power Tools", "Cordless Impact Driver 18V Kit", 1650000, 7,
     img("4338ca", "Impact Driver 18V"),
     spec("Brand: TorqPro", "Part No: CID-18-KIT", "Voltage: 18 V Li-ion", "Max torque: 180 Nm",
          "Includes: 2 batteries, charger, case", "Unit: kit", "Min. order: 1 kit")),
    ("Presisi Instrument Co.", "Sensors & Switches", "Inductive Proximity Sensor M12 NPN NO (4 mm)", 185000, 65,
     img("4338ca", "Proximity Sensor M12"),
     spec("Brand: Presita", "Part No: SNS-IND-M12-NO", "Sensing distance: 4 mm", "Output: NPN, normally open",
          "Supply: 10 - 30 VDC", "Unit: pcs", "Min. order: 1 pcs")),
]

# Descriptions for PT Angkasa products that seed.py created without one
ANGKASA_DESCRIPTIONS = {
    "MCB 10 Ampere Schneider": spec("Brand: Schneider", "Part No: MCB-1P-10A", "Rating: 1 pole, 10 A, C-curve",
                                    "Unit: pcs", "Min. order: 1 pcs"),
    "MCB 16 Ampere Mitsubishi": spec("Brand: Mitsubishi", "Part No: MCB-1P-16A", "Rating: 1 pole, 16 A, C-curve",
                                     "Unit: pcs", "Min. order: 1 pcs"),
    "Supreme NYM Cable 3x2.5mm": spec("Brand: Supreme", "Part No: NYM-3X2.5", "Conductor: 3 core x 2.5 mm2 copper",
                                      "Insulation: PVC", "Unit: roll (50 m)", "Min. order: 1 roll"),
    "Eterna NYA Cable 1x1.5mm": spec("Brand: Eterna", "Part No: NYA-1X1.5", "Conductor: 1 core x 1.5 mm2 copper",
                                     "Insulation: PVC", "Unit: roll (100 m)", "Min. order: 1 roll"),
    "Topindo Panel Box 30x40x15": spec("Brand: Topindo", "Part No: PB-304015", "Size: 300 x 400 x 150 mm",
                                       "Material: Powder-coated steel", "Unit: pcs", "Min. order: 1 pcs"),
}

DEMO_ORDERS = [
    # (supplier store, status, [(product name, qty)])
    ("Bandung Bearing & Transmission", "delivered", [("Deep Groove Ball Bearing 6204-2RS", 20), ("V-Belt B-52", 4)]),
    ("Pneumatik Nusantara", "shipped", [("Double-Acting Pneumatic Cylinder 32 x 100 mm", 4),
                                        ("Push-in Fitting Straight 8 mm - 1/4 in (pack of 10)", 3)]),
    (ANGKASA, "processing", [("Contactor 9A 3P 24VAC Coil", 6), ("MCCB 3P 100A 25kA", 2)]),
    ("Safetyline Industrial Supply", "pending", [("Safety Helmet ABS with Ratchet Suspension", 25),
                                                 ("Nitrile-Coated Work Gloves Size L (pair)", 48)]),
]
DEMO_ADDRESS = "Kawasan Industri Rancaekek, Jl. Raya Bandung-Garut Km 22, Bandung, Jawa Barat 40394"


def run_seeder():
    password = os.getenv("DEMO_BUYER_PASSWORD")
    if not password:
        sys.exit("DEMO_BUYER_PASSWORD is not set. Example: DEMO_BUYER_PASSWORD='...' python seed_industrial.py")

    with app.app_context():
        print("=== STARTING INDUSTRIAL CATALOG SEEDING ===")
        try:
            # 1. Categories
            cats = {c.name: c for c in Categories.query.all()}
            for name, desc, parent in CATEGORIES:
                if name not in cats:
                    cat = Categories(name=name, description=desc,
                                     parent_id=cats[parent].id if parent else None)
                    db.session.add(cat)
                    db.session.flush()
                    cats[name] = cat
            print(f"[1/5] Categories ready ({len(CATEGORIES)} industrial categories ensured).")

            # 2. Suppliers (users + sellers). Supplier passwords are random and never shown:
            #    nobody needs to log in as them, they only own catalog data.
            sellers = {s.store_name: s for s in Sellers.query.all()}
            for store, email, full_name, desc in NEW_SUPPLIERS:
                if store in sellers:
                    continue
                user = Users.query.filter_by(email=email).first()
                if not user:
                    user = Users(email=email, full_name=full_name, role="user")
                    user.set_password(secrets.token_urlsafe(24))
                    db.session.add(user)
                    db.session.flush()
                seller = Sellers(id=user.id, store_name=store, store_description=desc,
                                 avatar_url=f"https://dummyimage.com/200x200/1f2937/f9fafb&text={store.split()[0]}")
                db.session.add(seller)
                db.session.flush()
                sellers[store] = seller
            print("[2/5] Demo suppliers ready.")

            # 3. Products
            products = {p.name: p for p in Products.query.all()}
            created = 0
            for store, cat_name, name, price, stock, image, description in PRODUCTS:
                if name in products:
                    continue
                product = Products(category_id=cats[cat_name].id, seller_id=sellers[store].id, name=name,
                                   slug=generate_unique_slug(name), price=price, stock=stock,
                                   image_url=image, description=description, is_active=True)
                db.session.add(product)
                db.session.flush()
                products[name] = product
                created += 1
            for name, description in ANGKASA_DESCRIPTIONS.items():
                existing = products.get(name)
                if existing and not existing.description:
                    existing.description = description
            print(f"[3/5] Industrial products ready ({created} new).")

            # 4. Deactivate legacy, non-industrial demo products (soft delete only)
            legacy_ids = [s.id for s in Sellers.query.filter(Sellers.store_name.in_(LEGACY_STORES)).all()]
            deactivated = 0
            if legacy_ids:
                for p in Products.query.filter(Products.seller_id.in_(legacy_ids), Products.is_active.is_(True)).all():
                    p.is_active = False
                    deactivated += 1
            print(f"[4/5] Legacy demo products deactivated: {deactivated}.")

            # 5. Demo buyer + orders
            buyer = Users.query.filter_by(email=DEMO_BUYER_EMAIL).first()
            if not buyer:
                buyer = Users(email=DEMO_BUYER_EMAIL, full_name=DEMO_BUYER_NAME, role="user")
                buyer.set_password(password)
                db.session.add(buyer)
                db.session.flush()
            if Orders.query.filter_by(user_id=buyer.id).first():
                print("[5/5] Demo buyer already has orders, skipping.")
            else:
                for store, status, items in DEMO_ORDERS:
                    lines = [(products[n], qty) for n, qty in items]
                    total = sum(float(p.price) * qty for p, qty in lines)
                    order = Orders(user_id=buyer.id, seller_id=sellers[store].id, status=status,
                                   total_amount=total, shipping_address=DEMO_ADDRESS)
                    db.session.add(order)
                    db.session.flush()
                    for p, qty in lines:
                        db.session.add(OrderItems(order_id=order.id, product_id=p.id, quantity=qty,
                                                  unit_price=p.price))
                print("[5/5] Demo buyer and sample orders created.")

            db.session.commit()
            print("=== INDUSTRIAL SEEDING COMPLETED SUCCESSFULLY ===")
        except IntegrityError as e:
            db.session.rollback()
            print(f"[FAILED] Relational key violation: {e}")
        except Exception as e:
            db.session.rollback()
            print(f"[FAILED] Unexpected error: {e}")
            raise


if __name__ == "__main__":
    run_seeder()
