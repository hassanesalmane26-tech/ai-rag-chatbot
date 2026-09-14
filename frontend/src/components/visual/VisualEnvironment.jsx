import sanctuaryScene from "../../assets/trident-celestial-sanctuary.svg";
import skylineScene from "../../assets/trident-celestial-skyline.svg";
import foregroundScene from "../../assets/trident-celestial-foreground.svg";
import celestialWorld from "../../assets/trident-celestial-world.webp";

export default function VisualEnvironment() {
  return (
    <div className="trident-environment" aria-hidden="true">
      <div className="trident-environment__stars" />
      <div className="trident-environment__deep-stars" />
      <img className="trident-environment__world-art" src={celestialWorld} alt="" />
      <div className="trident-environment__constellations"><i /><i /><i /></div>
      <div className="trident-environment__moon" />
      <div className="trident-environment__nebula"><i /><i /></div>
      <div className="trident-environment__clouds trident-environment__clouds--high"><i /><i /><i /></div>
      <div className="trident-environment__clouds trident-environment__clouds--low"><i /><i /><i /></div>
      <div className="trident-environment__cloudbank"><i /><i /><i /><i /><i /></div>
      <img className="trident-environment__scene-art trident-environment__scene-art--far" src={skylineScene} alt="" />
      <img className="trident-environment__scene-art trident-environment__scene-art--mid" src={sanctuaryScene} alt="" />
      <div className="trident-environment__mist trident-environment__mist--near" />
      <div className="trident-environment__mist trident-environment__mist--far" />
      <div className="trident-environment__grid" />
      <div className="trident-environment__architecture trident-environment__architecture--left" />
      <div className="trident-environment__architecture trident-environment__architecture--right" />
      <div className="trident-environment__vault trident-environment__vault--left" />
      <div className="trident-environment__vault trident-environment__vault--right" />
      <div className="trident-environment__horizon" />
      <div className="trident-environment__city trident-environment__city--far"><i /><i /><i /><i /><i /><i /><i /><i /><i /></div>
      <div className="trident-environment__city trident-environment__city--near"><i /><i /><i /><i /><i /><i /><i /></div>
      <div className="trident-environment__skyline trident-environment__skyline--left"><i /><i /><i /><i /></div>
      <div className="trident-environment__skyline trident-environment__skyline--right"><i /><i /><i /><i /></div>
      <div className="trident-environment__arcade trident-environment__arcade--left"><i /><i /><i /></div>
      <div className="trident-environment__arcade trident-environment__arcade--right"><i /><i /><i /></div>
      <div className="trident-environment__bridges"><i /><i /><i /></div>
      <div className="trident-environment__causeway"><i /><i /><i /></div>
      <div className="trident-environment__citadel"><i /><i /><i /><i /><i /></div>
      <div className="trident-environment__sanctuary"><i /><i /><i /><i /><i /><i /><i /></div>
      <div className="trident-environment__crown"><i /><i /><i /></div>
      <div className="trident-environment__lightwell"><i /><i /></div>
      <div className="trident-environment__axis" />
      <div className="trident-environment__world" />
      <div className="trident-environment__portal"><i /><i /><i /></div>
      <div className="trident-environment__floor" />
      <div className="trident-environment__terraces"><i /><i /><i /></div>
      <div className="trident-environment__foreground"><i /><i /></div>
      <img className="trident-environment__scene-art trident-environment__scene-art--near" src={foregroundScene} alt="" />
      <div className="trident-environment__orbit trident-environment__orbit--one" />
      <div className="trident-environment__orbit trident-environment__orbit--two" />
      <div className="trident-environment__beam trident-environment__beam--one" />
      <div className="trident-environment__beam trident-environment__beam--two" />
      <div className="trident-orb trident-orb--electric" />
      <div className="trident-orb trident-orb--cyan" />
      <div className="trident-orb trident-orb--violet" />
      <div className="trident-particles"><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /></div>
    </div>
  );
}
