import sys

filepath = 'from-plant-to-watershed/frontend/src/app/(dashboard)/simulations/page.tsx'

with open(filepath, 'r') as f:
    content = f.read()

# 1. Update state
old_state = """  // Navegación de vistas y disposición innovadora
  const [activeTab, setActiveTab] = useState<"RUNS" | "VALIDATION" | "SCENARIOS" | "STATISTICS">("RUNS");
  const [simDetailTab, setSimDetailTab] = useState<"CHARTS" | "AI" | "SPECIFICATIONS">("CHARTS");
  const [chartViewMode, setChartViewMode] = useState<"ALL" | "STREAMFLOW" | "PLANT" | "SOIL" | "MONTHLY">("STREAMFLOW");
  const [chartLayout, setChartLayout] = useState<"GRID" | "SPOTLIGHT" | "STACK">("GRID");
  const [expandedChartModal, setExpandedChartModal] = useState<"MONTHLY" | "STREAMFLOW" | "PLANT" | "SOIL" | null>(null);
  const [isCatalogCollapsed, setIsCatalogCollapsed] = useState(false);

  // Listener para cerrar modal con tecla Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setExpandedChartModal(null);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);"""

new_state = """  // Navegación de vistas y disposición por modales
  const [activeTab, setActiveTab] = useState<"RUNS" | "VALIDATION" | "SCENARIOS" | "STATISTICS">("RUNS");
  const [activeModalTab, setActiveModalTab] = useState<"CHARTS" | "AI" | "SPECIFICATIONS" | null>(null);
  const [chartViewMode, setChartViewMode] = useState<"ALL" | "STREAMFLOW" | "PLANT" | "SOIL" | "MONTHLY">("STREAMFLOW");
  const [chartLayout, setChartLayout] = useState<"GRID" | "SPOTLIGHT" | "STACK">("GRID");
  const [expandedChartModal, setExpandedChartModal] = useState<"MONTHLY" | "STREAMFLOW" | "PLANT" | "SOIL" | null>(null);
  const [isCatalogCollapsed, setIsCatalogCollapsed] = useState(false);

  // Listener para cerrar modales con tecla Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setActiveModalTab(null);
        setExpandedChartModal(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);"""

if old_state in content:
    content = content.replace(old_state, new_state)
    print("State updated")
else:
    print("State NOT found")
    sys.exit(1)

with open(filepath, 'w') as f:
    f.write(content)

