import celestialWorld from "../../assets/trident-celestial-world.webp";

// The illustrated city supplies material detail without hundreds of live glass layers.
export default function VisualEnvironment() {
  return <div className="trident-environment" aria-hidden="true">
    <img className="trident-environment__world-art trident-environment__sanctuary" src={celestialWorld} alt="" decoding="async" fetchPriority="high" />
    <div className="trident-environment__stars trident-environment__constellations" />
    <div className="trident-environment__axis" />
    <div className="trident-environment__portal" />
    <div className="trident-environment__mist trident-environment__clouds--low" />
    <div className="trident-environment__foreground trident-environment__floor" />
  </div>;
}
