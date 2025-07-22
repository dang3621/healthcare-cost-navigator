#!/usr/bin/env python3
"""
ETL script for Healthcare Cost Navigator
Loads CMS hospital pricing data and generates mock ratings
"""

import asyncio
import pandas as pd
import random
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.core.database import engine, AsyncSessionLocal
from app.models.base import Base
from app.models.provider import Provider
from app.models.rating import Rating


async def create_tables():
    """Create database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created")


async def load_providers_data(csv_file: str = "data/sample_prices_ny.csv"):
    """Load provider data from CSV"""
    print(f"📊 Loading provider data from {csv_file}")
    
    # Read CSV file with encoding handling
    try:
        df = pd.read_csv(csv_file, encoding='utf-8')
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(csv_file, encoding='latin-1')
        except UnicodeDecodeError:
            df = pd.read_csv(csv_file, encoding='cp1252')
    
    print(f"📈 Loaded {len(df)} records from CSV")
    
    # Map CMS column names to our schema
    column_mapping = {
        'Rndrng_Prvdr_CCN': 'provider_id',
        'Rndrng_Prvdr_Org_Name': 'provider_name',
        'Rndrng_Prvdr_City': 'provider_city',
        'Rndrng_Prvdr_State_Abrvtn': 'provider_state',
        'Rndrng_Prvdr_Zip5': 'provider_zip_code',
        'DRG_Desc': 'ms_drg_definition',
        'Tot_Dschrgs': 'total_discharges',
        'Avg_Submtd_Cvrd_Chrg': 'average_covered_charges',
        'Avg_Tot_Pymt_Amt': 'average_total_payments',
        'Avg_Mdcr_Pymt_Amt': 'average_medicare_payments'
    }
    
    # Rename columns
    df = df.rename(columns=column_mapping)
    
    # Add DRG code to description for better matching
    if 'DRG_Cd' in df.columns:
        df['ms_drg_definition'] = df['DRG_Cd'].astype(str) + ' - ' + df['ms_drg_definition']
    
    # Clean and validate data
    df = df.dropna(subset=['provider_id', 'provider_name', 'ms_drg_definition'])
    df['provider_id'] = df['provider_id'].astype(str)
    df['provider_zip_code'] = df['provider_zip_code'].astype(str)
    df['total_discharges'] = pd.to_numeric(df['total_discharges'], errors='coerce').fillna(0).astype(int)
    df['average_covered_charges'] = pd.to_numeric(df['average_covered_charges'], errors='coerce').fillna(0.0)
    df['average_total_payments'] = pd.to_numeric(df['average_total_payments'], errors='coerce').fillna(0.0)
    df['average_medicare_payments'] = pd.to_numeric(df['average_medicare_payments'], errors='coerce').fillna(0.0)
    
    print(f"🧹 Cleaned data: {len(df)} valid records")
    
    # Insert data into database
    async with AsyncSessionLocal() as session:
        providers_added = 0
        
        for _, row in df.iterrows():
            # Check if provider already exists by provider_id
            result = await session.execute(
                select(Provider).where(Provider.provider_id == row['provider_id'])
            )
            existing = result.scalar_one_or_none()
            if existing:
                continue
                
            provider = Provider(
                provider_id=row['provider_id'],
                provider_name=row['provider_name'],
                provider_city=row['provider_city'],
                provider_state=row['provider_state'],
                provider_zip_code=row['provider_zip_code'],
                ms_drg_definition=row['ms_drg_definition'],
                total_discharges=row['total_discharges'],
                average_covered_charges=row['average_covered_charges'],
                average_total_payments=row['average_total_payments'],
                average_medicare_payments=row['average_medicare_payments']
            )
            
            session.add(provider)
            providers_added += 1
            
            # Commit in batches
            if providers_added % 100 == 0:
                await session.commit()
                print(f"💾 Committed {providers_added} providers")
        
        await session.commit()
        print(f"✅ Successfully loaded {providers_added} providers")


async def generate_mock_ratings():
    """Generate mock star ratings for providers"""
    print("⭐ Generating mock ratings")
    
    async with AsyncSessionLocal() as session:
        # Get all unique provider IDs
        result = await session.execute(text("SELECT DISTINCT provider_id FROM providers"))
        provider_ids = [row[0] for row in result.fetchall()]
        
        ratings_added = 0
        
        for provider_id in provider_ids:
            # Generate 1-3 ratings per provider
            num_ratings = random.randint(1, 3)
            
            for i in range(num_ratings):
                rating_type = random.choice(['overall', 'quality', 'safety', 'patient_experience'])
                
                # Generate realistic ratings (skewed towards higher ratings)
                rating_value = round(random.triangular(6.0, 10.0, 8.5), 1)
                
                rating = Rating(
                    provider_id=provider_id,
                    rating=rating_value,
                    rating_type=rating_type
                )
                
                session.add(rating)
                ratings_added += 1
        
        await session.commit()
        print(f"✅ Generated {ratings_added} mock ratings")


async def verify_data():
    """Verify loaded data"""
    print("🔍 Verifying loaded data")
    
    async with AsyncSessionLocal() as session:
        # Count providers
        provider_count = await session.execute(text("SELECT COUNT(*) FROM providers"))
        provider_total = provider_count.scalar()
        
        # Count ratings
        rating_count = await session.execute(text("SELECT COUNT(*) FROM ratings"))
        rating_total = rating_count.scalar()
        
        # Sample data
        sample_provider = await session.execute(
            text("SELECT provider_name, provider_city, ms_drg_definition FROM providers LIMIT 1")
        )
        sample = sample_provider.fetchone()
        
        print(f"📊 Database Summary:")
        print(f"   - Providers: {provider_total}")
        print(f"   - Ratings: {rating_total}")
        if sample:
            print(f"   - Sample: {sample[0]} in {sample[1]} - {sample[2]}")


async def main():
    """Main ETL process"""
    print("🚀 Starting Healthcare Cost Navigator ETL")
    
    try:
        # Create tables
        await create_tables()
        
        # Load provider data
        await load_providers_data()
        
        # Generate mock ratings
        await generate_mock_ratings()
        
        # Verify data
        await verify_data()
        
        print("✅ ETL process completed successfully!")
        
    except Exception as e:
        print(f"❌ ETL process failed: {e}")
        raise
    
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
