export default function VisualEnvironment() {
  return (
    <div className="trident-environment" aria-hidden="true">
      <div className="trident-environment__grid" />
      <div className="trident-environment__architecture trident-environment__architecture--left" />
      <div className="trident-environment__architecture trident-environment__architecture--right" />
      <div className="trident-environment__horizon" />
      <div className="trident-environment__world" />
      <div className="trident-environment__orbit trident-environment__orbit--one" />
      <div className="trident-environment__orbit trident-environment__orbit--two" />
      <div className="trident-environment__beam trident-environment__beam--one" />
      <div className="trident-environment__beam trident-environment__beam--two" />
      <div className="trident-orb trident-orb--electric" />
      <div className="trident-orb trident-orb--cyan" />
      <div className="trident-orb trident-orb--violet" />
      <div className="trident-particles"><i /><i /><i /><i /><i /><i /><i /><i /></div>
    </div>
  );
}
