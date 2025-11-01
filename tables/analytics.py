import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Configurações de visualização
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")
plt.rcParams['figure.figsize'] = (12, 8)

def load_and_explore_data():
    """Carrega e explora as tabelas do dataset imobiliário"""
    
    # Carregar as tabelas
    buildings = pd.read_excel('buildings.xlsx')
    typologies = pd.read_excel('typologies.xlsx')
    units = pd.read_excel('units.xlsx')
    units_updates = pd.read_excel('units_updates.xlsx')
    
    print("=" * 80)
    print("ANÁLISE EXPLORATÓRIA DO DATASET IMOBILIÁRIO")
    print("=" * 80)
    
    return buildings, typologies, units, units_updates

def basic_data_overview(df, df_name):
    """Fornece visão geral básica dos dados"""
    print(f"\n{'='*50}")
    print(f"VISÃO GERAL: {df_name.upper()}")
    print(f"{'='*50}")
    
    print(f"Shape: {df.shape}")
    print(f"\nTipos de dados:")
    print(df.dtypes)
    
    print(f"\nPrimeiras 5 linhas:")
    print(df.head())
    
    print(f"\nEstatísticas descritivas:")
    print(df.describe(include='all'))
    
    print(f"\nValores nulos por coluna:")
    null_counts = df.isnull().sum()
    for col, null_count in null_counts.items():
        if null_count > 0:
            print(f"  {col}: {null_count} ({null_count/len(df)*100:.2f}%)")

def analyze_buildings(buildings):
    """Análise específica da tabela de edificações"""
    print(f"\n{'='*50}")
    print("ANÁLISE DETALHADA: BUILDINGS")
    print(f"{'='*50}")
    
    # Análise de localização
    print("\n📊 DISTRIBUIÇÃO GEOGRÁFICA:")
    print(f"Cidades presentes: {buildings['cidade_endereço'].nunique()}")
    print(f"Estados presentes: {buildings['estado_endereço'].nunique()}")
    print(f"\nTop 5 cidades:")
    print(buildings['cidade_endereço'].value_counts().head())
    
    # Análise de status e estágios
    print(f"\n🏗️ STATUS DOS EMPREENDIMENTOS:")
    print(buildings['status'].value_counts())
    print(f"\nESTÁGIOS:")
    print(buildings['estagio'].value_counts())
    
    # Análise de incorporadoras
    print(f"\n🏢 INCORPORADORAS:")
    print(f"Total de incorporadoras: {buildings['incorporadora_nome'].nunique()}")
    print(f"Top 10 incorporadoras:")
    print(buildings['incorporadora_nome'].value_counts().head(10))
    
    # Análise temporal
    print(f"\n📅 ANÁLISE TEMPORAL:")
    if 'data_lançamento' in buildings.columns:
        buildings['data_lançamento'] = pd.to_datetime(buildings['data_lançamento'], errors='coerce')
        print(f"Período de lançamentos: {buildings['data_lançamento'].min()} a {buildings['data_lançamento'].max()}")
    
    if 'data_entrega' in buildings.columns:
        buildings['data_entrega'] = pd.to_datetime(buildings['data_entrega'], errors='coerce')
        print(f"Período de entregas: {buildings['data_entrega'].min()} a {buildings['data_entrega'].max()}")

def analyze_typologies(typologies):
    """Análise específica da tabela de tipologias"""
    print(f"\n{'='*50}")
    print("ANÁLISE DETALHADA: TYPOLOGIES")
    print(f"{'='*50}")
    
    # Análise de configurações
    print("\n🛏️ CONFIGURAÇÕES DAS TIPOLOGIAS:")
    
    numeric_cols = ['area_privada', 'area_total', 'quartos', 'banheiros', 'suites', 'lavabo', 'vagas_estacionamento']
    for col in numeric_cols:
        if col in typologies.columns:
            print(f"\n{col.upper()}:")
            print(f"  Média: {typologies[col].mean():.2f}")
            print(f"  Mediana: {typologies[col].median():.2f}")
            print(f"  Std: {typologies[col].std():.2f}")
            print(f"  Min: {typologies[col].min()} | Max: {typologies[col].max()}")
    
    # Análise de tipos de tipologia
    if 'tipo' in typologies.columns:
        print(f"\n📋 TIPOS DE TIPOLOGIA:")
        print(typologies['tipo'].value_counts())

def analyze_units(units):
    """Análise específica da tabela de unidades"""
    print(f"\n{'='*50}")
    print("ANÁLISE DETALHADA: UNITS")
    print(f"{'='*50}")
    
    print(f"\n🏠 INFORMAÇÕES DAS UNIDADES:")
    print(f"Total de unidades: {len(units)}")
    print(f"Prédios únicos: {units['id_predio'].nunique()}")
    print(f"Tipologias únicas: {units['id_tipologia'].nunique()}")
    
    # Análise de andares
    if 'andar' in units.columns:
        print(f"\n🏢 DISTRIBUIÇÃO POR ANDAR:")
        print(f"Andar mínimo: {units['andar'].min()}")
        print(f"Andar máximo: {units['andar'].max()}")
        print(f"Média de andares: {units['andar'].mean():.2f}")

def analyze_units_updates(units_updates):
    """Análise específica da tabela de atualizações"""
    print(f"\n{'='*50}")
    print("ANÁLISE DETALHADA: UNITS_UPDATES")
    print(f"{'='*50}")
    
    print(f"\n💰 ANÁLISE DE PREÇOS:")
    if 'preço' in units_updates.columns:
        print(f"Preço médio: R$ {units_updates['preço'].mean():.2f}")
        print(f"Preço mínimo: R$ {units_updates['preço'].min():.2f}")
        print(f"Preço máximo: R$ {units_updates['preço'].max():.2f}")
        print(f"Mediana: R$ {units_updates['preço'].median():.2f}")
    
    # Análise de disponibilidade
    if 'disponivel' in units_updates.columns:
        print(f"\n📈 DISPONIBILIDADE:")
        print(units_updates['disponivel'].value_counts())
    
    # Análise temporal
    if 'atualizado_em' in units_updates.columns:
        units_updates['atualizado_em'] = pd.to_datetime(units_updates['atualizado_em'], errors='coerce')
        print(f"\n⏰ PERÍODO DAS ATUALIZAÇÕES:")
        print(f"De: {units_updates['atualizado_em'].min()}")
        print(f"Até: {units_updates['atualizado_em'].max()}")

def create_visualizations(buildings, typologies, units, units_updates):
    """Cria visualizações para análise exploratória"""
    
    # 1. Distribuição geográfica
    fig, axes = plt.subplots(2, 2, figsize=(20, 15))
    
    # Distribuição por cidade
    if 'cidade_endereço' in buildings.columns:
        top_cities = buildings['cidade_endereço'].value_counts().head(10)
        axes[0,0].bar(top_cities.index, top_cities.values)
        axes[0,0].set_title('Top 10 Cidades com Mais Empreendimentos')
        axes[0,0].tick_params(axis='x', rotation=45)
    
    # Status dos empreendimentos
    if 'status' in buildings.columns:
        status_counts = buildings['status'].value_counts()
        axes[0,1].pie(status_counts.values, labels=status_counts.index, autopct='%1.1f%%')
        axes[0,1].set_title('Distribuição por Status')
    
    # Distribuição de áreas
    if 'area_privada' in typologies.columns:
        axes[1,0].hist(typologies['area_privada'].dropna(), bins=30, alpha=0.7)
        axes[1,0].set_title('Distribuição de Área Privada')
        axes[1,0].set_xlabel('Área (m²)')
        axes[1,0].set_ylabel('Frequência')
    
    # Distribuição de preços
    if 'preço' in units_updates.columns:
        axes[1,1].hist(units_updates['preço'].dropna(), bins=30, alpha=0.7, color='green')
        axes[1,1].set_title('Distribuição de Preços')
        axes[1,1].set_xlabel('Preço (R$)')
        axes[1,1].set_ylabel('Frequência')
    
    plt.tight_layout()
    plt.show()
    
    # 2. Análise de relações
    fig, axes = plt.subplots(2, 2, figsize=(20, 15))
    
    # Quartos vs Área
    if all(col in typologies.columns for col in ['quartos', 'area_privada']):
        sns.boxplot(data=typologies, x='quartos', y='area_privada', ax=axes[0,0])
        axes[0,0].set_title('Relação entre Quartos e Área Privada')
    
    # Distribuição de andares
    if 'andar' in units.columns:
        axes[0,1].hist(units['andar'].dropna(), bins=20, alpha=0.7, color='orange')
        axes[0,1].set_title('Distribuição de Andares')
        axes[0,1].set_xlabel('Andar')
        axes[0,1].set_ylabel('Frequência')
    
    # Preço ao longo do tempo
    if all(col in units_updates.columns for col in ['atualizado_em', 'preço']):
        units_updates['mes'] = units_updates['atualizado_em'].dt.to_period('M')
        price_trend = units_updates.groupby('mes')['preço'].mean()
        axes[1,0].plot(price_trend.index.astype(str), price_trend.values)
        axes[1,0].set_title('Evolução do Preço Médio ao Longo do Tempo')
        axes[1,0].tick_params(axis='x', rotation=45)
    
    # Heatmap de correlação para tipologias
    numeric_cols = typologies.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 1:
        correlation_matrix = typologies[numeric_cols].corr()
        sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', ax=axes[1,1])
        axes[1,1].set_title('Correlação entre Variáveis das Tipologias')
    
    plt.tight_layout()
    plt.show()

def data_quality_report(buildings, typologies, units, units_updates):
    """Relatório de qualidade dos dados"""
    
    print(f"\n{'='*60}")
    print("RELATÓRIO DE QUALIDADE DOS DADOS")
    print(f"{'='*60}")
    
    datasets = {
        'buildings': buildings,
        'typologies': typologies, 
        'units': units,
        'units_updates': units_updates
    }
    
    for name, df in datasets.items():
        print(f"\n📋 {name.upper()}:")
        print(f"   Total de registros: {len(df)}")
        print(f"   Total de colunas: {len(df.columns)}")
        print(f"   Valores nulos: {df.isnull().sum().sum()}")
        print(f"   Percentual de nulos: {df.isnull().sum().sum()/(len(df)*len(df.columns))*100:.2f}%")
        
        # Colunas com mais de 50% de valores nulos
        high_null_cols = []
        for col in df.columns:
            null_pct = df[col].isnull().sum() / len(df) * 100
            if null_pct > 50:
                high_null_cols.append((col, null_pct))
        
        if high_null_cols:
            print(f"   ⚠️  Colunas problemáticas (>50% nulos):")
            for col, pct in high_null_cols:
                print(f"      - {col}: {pct:.1f}% nulos")

def main():
    """Função principal"""
    
    # Carregar dados
    buildings, typologies, units, units_updates = load_and_explore_data()
    
    # Análises básicas
    basic_data_overview(buildings, 'buildings')
    basic_data_overview(typologies, 'typologies') 
    basic_data_overview(units, 'units')
    basic_data_overview(units_updates, 'units_updates')
    
    # Análises específicas
    analyze_buildings(buildings)
    analyze_typologies(typologies)
    analyze_units(units)
    analyze_units_updates(units_updates)
    
    # Relatório de qualidade
    data_quality_report(buildings, typologies, units, units_updates)
    
    # Visualizações
    print(f"\n{'='*50}")
    print("GERANDO VISUALIZAÇÕES...")
    print(f"{'='*50}")
    create_visualizations(buildings, typologies, units, units_updates)
    
    print(f"\n✅ ANÁLISE EXPLORATÓRIA CONCLUÍDA!")

if __name__ == "__main__":
    main()