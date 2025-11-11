import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Configurações de visualização
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")
plt.rcParams['figure.figsize'] = (14, 10)

def load_and_compare_excels():
    """Carrega e compara os Excel brutos vs limpos na sua estrutura"""
    
    # Verifica se as pastas existem
    raw_path = Path('tables')
    clean_path = Path('tables_cleaned')
    
    if not raw_path.exists():
        print(f"❌ Pasta 'tables' não encontrada!")
        return {}
    if not clean_path.exists():
        print(f"❌ Pasta 'tables_cleaned' não encontrada!")
        return {}
    
    # Mapeamento dos arquivos - baseado na sua estrutura
    file_mapping = {
        'buildings': ('buildings.xlsx', 'buildings_cleaned.xlsx'),
        'typologies': ('typologies.xlsx', 'typologies_cleaned.xlsx'),
        'units': ('units.xlsx', 'units_cleaned.xlsx'),
        'units_updates': ('units_updates.xlsx', 'units_updates_cleaned.xlsx')
    }
    
    print("=" * 80)
    print("COMPARAÇÃO: DADOS BRUTOS vs DADOS LIMPOS")
    print("=" * 80)
    
    results = {}
    
    for table_name, (raw_file, clean_file) in file_mapping.items():
        raw_file_path = raw_path / raw_file
        clean_file_path = clean_path / clean_file
        
        if raw_file_path.exists() and clean_file_path.exists():
            print(f"\n📊 ANALISANDO: {table_name}")
            print("-" * 50)
            
            try:
                # Carrega os dados
                df_raw = pd.read_excel(raw_file_path)
                df_clean = pd.read_excel(clean_file_path)
                
                # Realiza as comparações
                comparison = compare_table(df_raw, df_clean, table_name)
                results[table_name] = comparison
                
            except Exception as e:
                print(f"❌ Erro ao processar {table_name}: {e}")
                
        else:
            missing_files = []
            if not raw_file_path.exists():
                missing_files.append(f"bruto: {raw_file}")
            if not clean_file_path.exists():
                missing_files.append(f"limpo: {clean_file}")
            print(f"❌ Arquivos não encontrados para {table_name}: {', '.join(missing_files)}")
    
    return results

def compare_table(df_raw, df_clean, table_name):
    """Compara uma tabela específica"""
    
    comparison_results = {}
    
    # 1. Métricas básicas
    comparison_results['basic_metrics'] = compare_basic_metrics(df_raw, df_clean, table_name)
    
    # 2. Análise de valores nulos
    comparison_results['nulls_analysis'] = compare_nulls_analysis(df_raw, df_clean, table_name)
    
    # 3. Estatísticas numéricas
    comparison_results['numeric_stats'] = compare_numeric_stats(df_raw, df_clean, table_name)
    
    # 4. Análise categórica
    comparison_results['categorical_analysis'] = compare_categorical_analysis(df_raw, df_clean, table_name)
    
    # 5. Análise de dados
    comparison_results['data_quality'] = compare_data_quality(df_raw, df_clean, table_name)
    
    return comparison_results

def compare_basic_metrics(df_raw, df_clean, table_name):
    """Compara métricas básicas entre as versões"""
    
    print(f"📈 MÉTRICAS BÁSICAS - {table_name.upper()}")
    print("=" * 60)
    
    total_cells_raw = len(df_raw) * len(df_raw.columns)
    total_cells_clean = len(df_clean) * len(df_clean.columns)
    
    metrics_data = {
        'Métrica': ['Registros', 'Colunas', 'Valores Nulos', 'Completude (%)', 'Memória (MB)'],
        'Bruto': [
            len(df_raw),
            len(df_raw.columns),
            df_raw.isnull().sum().sum(),
            round((1 - df_raw.isnull().sum().sum() / total_cells_raw) * 100, 2),
            round(df_raw.memory_usage(deep=True).sum() / 1024**2, 2)
        ],
        'Limpo': [
            len(df_clean),
            len(df_clean.columns),
            df_clean.isnull().sum().sum(),
            round((1 - df_clean.isnull().sum().sum() / total_cells_clean) * 100, 2),
            round(df_clean.memory_usage(deep=True).sum() / 1024**2, 2)
        ]
    }
    
    metrics_df = pd.DataFrame(metrics_data)
    metrics_df['Diferença'] = metrics_df['Limpo'] - metrics_df['Bruto']
    metrics_df['Melhoria (%)'] = round((metrics_df['Limpo'] - metrics_df['Bruto']) / metrics_df['Bruto'].replace(0, 1) * 100, 2)
    
    print(metrics_df.to_string(index=False))
    print()
    
    return metrics_df

def compare_nulls_analysis(df_raw, df_clean, table_name):
    """Analisa e compara valores nulos"""
    
    print(f"🔍 ANÁLISE DE VALORES NULOS - {table_name.upper()}")
    print("=" * 60)
    
    # Encontra colunas problemáticas (mais de 50% nulos)
    problem_cols_raw = []
    problem_cols_clean = []
    
    for col in df_raw.columns:
        null_pct_raw = (df_raw[col].isnull().sum() / len(df_raw)) * 100
        if null_pct_raw > 50:
            problem_cols_raw.append((col, null_pct_raw))
    
    for col in df_clean.columns:
        null_pct_clean = (df_clean[col].isnull().sum() / len(df_clean)) * 100
        if null_pct_clean > 50:
            problem_cols_clean.append((col, null_pct_clean))
    
    if problem_cols_raw or problem_cols_clean:
        print("Colunas com >50% de valores nulos:")
        if problem_cols_raw:
            print("  BRUTO:", [f"{col}({pct:.1f}%)" for col, pct in problem_cols_raw])
        if problem_cols_clean:
            print("  LIMPO:", [f"{col}({pct:.1f}%)" for col, pct in problem_cols_clean])
    else:
        print("✅ Nenhuma coluna com mais de 50% de valores nulos")
    
    # Calcula redução de nulos por coluna
    null_reduction = []
    for col in df_raw.columns:
        if col in df_clean.columns:
            nulls_raw = df_raw[col].isnull().sum()
            nulls_clean = df_clean[col].isnull().sum()
            reduction = nulls_raw - nulls_clean
            if reduction != 0:
                null_reduction.append({
                    'Coluna': col,
                    'Nulos_Bruto': nulls_raw,
                    'Nulos_Limpo': nulls_clean,
                    'Redução': reduction,
                    'Redução_Pct': round((reduction / nulls_raw * 100) if nulls_raw > 0 else 0, 2)
                })
    
    if null_reduction:
        null_df = pd.DataFrame(null_reduction)
        print(f"\nColunas com redução de nulos (top 10):")
        display_cols = ['Coluna', 'Nulos_Bruto', 'Nulos_Limpo', 'Redução', 'Redução_Pct']
        print(null_df[display_cols].sort_values('Redução', ascending=False).head(10).round(2).to_string(index=False))
    else:
        print("✅ Nenhuma redução significativa de nulos")
    
    print()
    return null_reduction

def compare_numeric_stats(df_raw, df_clean, table_name):
    """Compara estatísticas de colunas numéricas"""
    
    numeric_cols_raw = df_raw.select_dtypes(include=[np.number]).columns
    numeric_cols_clean = df_clean.select_dtypes(include=[np.number]).columns
    
    common_numeric = set(numeric_cols_raw) & set(numeric_cols_clean)
    
    if not common_numeric:
        print(f"ℹ️ Nenhuma coluna numérica para comparar em {table_name}")
        return pd.DataFrame()
    
    print(f"📊 ESTATÍSTICAS NUMÉRICAS - {table_name.upper()}")
    print("=" * 60)
    
    stats_comparison = []
    
    for col in common_numeric:
        try:
            stats_raw = df_raw[col].describe()
            stats_clean = df_clean[col].describe()
            
            # Detecta outliers (valores beyond 3 std)
            mean_raw, std_raw = stats_raw['mean'], stats_raw['std']
            mean_clean, std_clean = stats_clean['mean'], stats_clean['std']
            
            if std_raw > 0:
                outliers_raw = len(df_raw[(df_raw[col] - mean_raw).abs() > 3 * std_raw])
            else:
                outliers_raw = 0
                
            if std_clean > 0:
                outliers_clean = len(df_clean[(df_clean[col] - mean_clean).abs() > 3 * std_clean])
            else:
                outliers_clean = 0
            
            stats_comparison.append({
                'Coluna': col,
                'Média_Bruto': round(stats_raw['mean'], 2),
                'Média_Limpo': round(stats_clean['mean'], 2),
                'Std_Bruto': round(stats_raw['std'], 2),
                'Std_Limpo': round(stats_clean['std'], 2),
                'Outliers_Bruto': outliers_raw,
                'Outliers_Limpo': outliers_clean,
                'Outliers_Removidos': outliers_raw - outliers_clean
            })
        except Exception as e:
            print(f"  ⚠️ Erro na coluna {col}: {e}")
    
    stats_df = pd.DataFrame(stats_comparison)
    
    if not stats_df.empty:
        # Filtra colunas com mudanças significativas
        significant_changes = stats_df[
            (abs(stats_df['Média_Bruto'] - stats_df['Média_Limpo']) > 0.1) |
            (stats_df['Outliers_Removidos'] > 0)
        ]
        
        if not significant_changes.empty:
            display_cols = ['Coluna', 'Média_Bruto', 'Média_Limpo', 'Std_Bruto', 'Std_Limpo', 'Outliers_Removidos']
            print(significant_changes[display_cols].to_string(index=False))
        else:
            print("✅ Nenhuma mudança significativa nas estatísticas numéricas")
    else:
        print("ℹ️ Nenhuma coluna numérica para comparar")
    
    print()
    return stats_df

def compare_categorical_analysis(df_raw, df_clean, table_name):
    """Analisa e compara colunas categóricas"""
    
    cat_cols_raw = df_raw.select_dtypes(include=['object']).columns
    cat_cols_clean = df_clean.select_dtypes(include=['object']).columns
    
    common_categorical = set(cat_cols_raw) & set(cat_cols_clean)
    
    if not common_categorical:
        print(f"ℹ️ Nenhuma coluna categórica para comparar em {table_name}")
        return pd.DataFrame()
    
    print(f"📝 ANÁLISE CATEGÓRICA - {table_name.upper()}")
    print("=" * 60)
    
    cat_comparison = []
    
    for col in common_categorical:
        try:
            # Verifica problemas de codificação
            encoding_issues_raw = df_raw[col].astype(str).str.contains('Ã|§|£|Â', na=False).sum()
            encoding_issues_clean = df_clean[col].astype(str).str.contains('Ã|§|£|Â', na=False).sum()
            
            # Conta valores únicos
            unique_raw = df_raw[col].nunique()
            unique_clean = df_clean[col].nunique()
            
            cat_comparison.append({
                'Coluna': col,
                'Valores_Únicos_Bruto': unique_raw,
                'Valores_Únicos_Limpo': unique_clean,
                'Problemas_Codificação_Bruto': encoding_issues_raw,
                'Problemas_Codificação_Limpo': encoding_issues_clean,
                'Redução_Categorias': unique_raw - unique_clean
            })
        except Exception as e:
            print(f"  ⚠️ Erro na coluna {col}: {e}")
    
    cat_df = pd.DataFrame(cat_comparison)
    
    if not cat_df.empty:
        # Filtra colunas com mudanças
        changed_cols = cat_df[
            (cat_df['Redução_Categorias'] != 0) | 
            (cat_df['Problemas_Codificação_Bruto'] > cat_df['Problemas_Codificação_Limpo'])
        ]
        
        if not changed_cols.empty:
            display_cols = ['Coluna', 'Valores_Únicos_Bruto', 'Valores_Únicos_Limpo', 
                           'Problemas_Codificação_Bruto', 'Problemas_Codificação_Limpo']
            print(changed_cols[display_cols].to_string(index=False))
        else:
            print("✅ Nenhuma mudança significativa nas colunas categóricas")
    else:
        print("ℹ️ Nenhuma coluna categórica para comparar")
    
    print()
    return cat_df

def compare_data_quality(df_raw, df_clean, table_name):
    """Analisa a qualidade geral dos dados"""
    
    print(f"✅ QUALIDADE DOS DADOS - {table_name.upper()}")
    print("=" * 60)
    
    quality_metrics = []
    
    # Verifica duplicatas
    dup_raw = df_raw.duplicated().sum()
    dup_clean = df_clean.duplicated().sum()
    quality_metrics.append(('Registros Duplicados', dup_raw, dup_clean))
    
    # Verifica valores extremos (para numéricas)
    numeric_cols = df_raw.select_dtypes(include=[np.number]).columns
    extreme_values_raw = 0
    extreme_values_clean = 0
    
    for col in numeric_cols:
        if col in df_clean.columns:
            try:
                if len(df_raw[col].dropna()) > 0:
                    q1 = df_raw[col].quantile(0.25)
                    q3 = df_raw[col].quantile(0.75)
                    iqr = q3 - q1
                    if iqr > 0:  # Evita divisão por zero
                        lower_bound = q1 - 1.5 * iqr
                        upper_bound = q3 + 1.5 * iqr
                        
                        extreme_raw = ((df_raw[col] < lower_bound) | (df_raw[col] > upper_bound)).sum()
                        extreme_clean = ((df_clean[col] < lower_bound) | (df_clean[col] > upper_bound)).sum()
                        
                        extreme_values_raw += extreme_raw
                        extreme_values_clean += extreme_clean
            except:
                continue
    
    quality_metrics.append(('Valores Extremos', extreme_values_raw, extreme_values_clean))
    
    # Verifica consistência de tipos
    type_changes = 0
    for col in df_raw.columns:
        if col in df_clean.columns:
            if df_raw[col].dtype != df_clean[col].dtype:
                type_changes += 1
    
    quality_metrics.append(('Mudanças de Tipo', type_changes, 0))
    
    quality_df = pd.DataFrame(quality_metrics, columns=['Métrica', 'Bruto', 'Limpo'])
    quality_df['Melhoria'] = quality_df['Bruto'] - quality_df['Limpo']
    
    print(quality_df.to_string(index=False))
    print()
    
    return quality_df

def generate_summary_report(results):
    """Gera um relatório resumido da comparação"""
    
    if not results:
        print("❌ Nenhum resultado para gerar relatório")
        return
    
    print("=" * 80)
    print("📋 RELATÓRIO RESUMO - COMPARAÇÃO GERAL")
    print("=" * 80)
    
    summary_data = []
    
    for table_name, comparison in results.items():
        basic_metrics = comparison['basic_metrics']
        
        summary_data.append({
            'Tabela': table_name,
            'Registros_Bruto': basic_metrics[basic_metrics['Métrica'] == 'Registros']['Bruto'].iloc[0],
            'Registros_Limpo': basic_metrics[basic_metrics['Métrica'] == 'Registros']['Limpo'].iloc[0],
            'Nulos_Bruto': basic_metrics[basic_metrics['Métrica'] == 'Valores Nulos']['Bruto'].iloc[0],
            'Nulos_Limpo': basic_metrics[basic_metrics['Métrica'] == 'Valores Nulos']['Limpo'].iloc[0],
            'Completude_Bruto': basic_metrics[basic_metrics['Métrica'] == 'Completude (%)']['Bruto'].iloc[0],
            'Completude_Limpo': basic_metrics[basic_metrics['Métrica'] == 'Completude (%)']['Limpo'].iloc[0]
        })
    
    summary_df = pd.DataFrame(summary_data)
    
    # Calcula totais
    total_records_raw = summary_df['Registros_Bruto'].sum()
    total_records_clean = summary_df['Registros_Limpo'].sum()
    total_nulls_raw = summary_df['Nulos_Bruto'].sum()
    total_nulls_clean = summary_df['Nulos_Limpo'].sum()
    avg_completude_raw = summary_df['Completude_Bruto'].mean()
    avg_completude_clean = summary_df['Completude_Limpo'].mean()
    
    print(f"📈 ESTATÍSTICAS GERAIS:")
    print(f"   • Total de registros: {total_records_raw:,} → {total_records_clean:,} "
          f"({((total_records_clean - total_records_raw) / total_records_raw * 100):+.1f}%)")
    print(f"   • Valores nulos: {total_nulls_raw:,} → {total_nulls_clean:,} "
          f"({((total_nulls_clean - total_nulls_raw) / total_nulls_raw * 100) if total_nulls_raw > 0 else 0:+.1f}%)")
    print(f"   • Completude média: {avg_completude_raw:.1f}% → {avg_completude_clean:.1f}% "
          f"({(avg_completude_clean - avg_completude_raw):+.1f}%)")
    
    print(f"\n📊 DETALHES POR TABELA:")
    print(summary_df.to_string(index=False))
    
    return summary_df

def create_comparison_charts(results):
    """Cria gráficos comparativos"""
    
    if not results:
        return
    
    summary_data = []
    for table_name, comparison in results.items():
        basic_metrics = comparison['basic_metrics']
        summary_data.append({
            'Tabela': table_name,
            'Completude_Bruto': basic_metrics[basic_metrics['Métrica'] == 'Completude (%)']['Bruto'].iloc[0],
            'Completude_Limpo': basic_metrics[basic_metrics['Métrica'] == 'Completude (%)']['Limpo'].iloc[0],
            'Nulos_Bruto': basic_metrics[basic_metrics['Métrica'] == 'Valores Nulos']['Bruto'].iloc[0],
            'Nulos_Limpo': basic_metrics[basic_metrics['Métrica'] == 'Valores Nulos']['Limpo'].iloc[0]
        })
    
    summary_df = pd.DataFrame(summary_data)
    
    # Cria os gráficos
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # Gráfico 1: Completude por tabela
    x = np.arange(len(summary_df))
    width = 0.35
    
    axes[0,0].bar(x - width/2, summary_df['Completude_Bruto'], width, label='Bruto', alpha=0.7, color='red')
    axes[0,0].bar(x + width/2, summary_df['Completude_Limpo'], width, label='Limpo', alpha=0.7, color='green')
    axes[0,0].set_title('Completude por Tabela', fontsize=14, fontweight='bold')
    axes[0,0].set_xlabel('Tabela')
    axes[0,0].set_ylabel('Completude (%)')
    axes[0,0].set_xticks(x)
    axes[0,0].set_xticklabels(summary_df['Tabela'], rotation=45)
    axes[0,0].legend()
    axes[0,0].grid(True, alpha=0.3)
    
    # Gráfico 2: Redução de nulos
    summary_df['Redução_Nulos'] = summary_df['Nulos_Bruto'] - summary_df['Nulos_Limpo']
    axes[0,1].bar(summary_df['Tabela'], summary_df['Redução_Nulos'], color='blue', alpha=0.7)
    axes[0,1].set_title('Redução de Valores Nulos', fontsize=14, fontweight='bold')
    axes[0,1].set_xlabel('Tabela')
    axes[0,1].set_ylabel('Nulos Removidos')
    axes[0,1].tick_params(axis='x', rotation=45)
    axes[0,1].grid(True, alpha=0.3)
    
    # Gráfico 3: Melhoria em completude
    summary_df['Melhoria_Completude'] = summary_df['Completude_Limpo'] - summary_df['Completude_Bruto']
    colors = ['green' if x >= 0 else 'red' for x in summary_df['Melhoria_Completude']]
    axes[1,0].bar(summary_df['Tabela'], summary_df['Melhoria_Completude'], color=colors, alpha=0.7)
    axes[1,0].set_title('Melhoria na Completude', fontsize=14, fontweight='bold')
    axes[1,0].set_xlabel('Tabela')
    axes[1,0].set_ylabel('Ganho em Completude (%)')
    axes[1,0].tick_params(axis='x', rotation=45)
    axes[1,0].grid(True, alpha=0.3)
    
    # Gráfico 4: Comparação de registros
    axes[1,1].bar(x - width/2, summary_df['Completude_Bruto'], width, label='Bruto', alpha=0.7, color='orange')
    axes[1,1].bar(x + width/2, summary_df['Completude_Limpo'], width, label='Limpo', alpha=0.7, color='purple')
    axes[1,1].set_title('Evolução da Qualidade', fontsize=14, fontweight='bold')
    axes[1,1].set_xlabel('Tabela')
    axes[1,1].set_ylabel('Completude (%)')
    axes[1,1].set_xticks(x)
    axes[1,1].set_xticklabels(summary_df['Tabela'], rotation=45)
    axes[1,1].legend()
    axes[1,1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

# Executa a comparação
if __name__ == "__main__":
    print("🔍 INICIANDO COMPARAÇÃO ENTRE DADOS BRUTOS E LIMPOS...")
    print("Estrutura esperada:")
    print("  tables/")
    print("    buildings.xlsx")
    print("    typologies.xlsx") 
    print("    units.xlsx")
    print("    units_updates.xlsx")
    print("  tables_cleaned/")
    print("    buildings_cleaned.xlsx")
    print("    typologies_cleaned.xlsx")
    print("    units_cleaned.xlsx")
    print("    units_updates_cleaned.xlsx")
    print()
    
    results = load_and_compare_excels()
    
    if results:
        summary = generate_summary_report(results)
        create_comparison_charts(results)
        print("\n✅ COMPARAÇÃO CONCLUÍDA!")
    else:
        print("\n❌ Nenhum resultado para exibir. Verifique se os arquivos estão nas pastas corretas.")