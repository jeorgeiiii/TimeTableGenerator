import React, { useMemo } from "react";

const SpaceScene: React.FC = () => {
  const stars = useMemo(() => {
    return Array.from({ length: 80 }, (_, i) => ({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: Math.random() * 2.5 + 0.5,
      duration: Math.random() * 4 + 2,
      delay: Math.random() * 5,
    }));
  }, []);

  // Extra stars clustered specifically around the sun (which sits at
  // top: -8%, left: 50%), scattered in a ring around it rather than the
  // uniform full-page spread above.
  const sunStars = useMemo(() => {
    return Array.from({ length: 35 }, (_, i) => {
      const angle = Math.random() * Math.PI * 2;
      const radius = 15 + Math.random() * 28; // % units from the sun's center
      return {
        id: i,
        x: 50 + Math.cos(angle) * radius * 1.3, // wider spread horizontally
        y: 8 + Math.sin(angle) * radius * 0.6,  // flatter spread vertically
        size: Math.random() * 2 + 0.5,
        duration: Math.random() * 3 + 1.5,
        delay: Math.random() * 5,
      };
    }).filter((s) => s.x >= 0 && s.x <= 100 && s.y >= -5 && s.y <= 45);
  }, []);

  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none">
      {/* Deep space gradient */}
      <div
        className="absolute inset-0"
        style={{
          background: `
            radial-gradient(ellipse 120% 80% at 50% -10%, hsl(var(--sun-corona) / 0.12) 0%, transparent 60%),
            radial-gradient(ellipse 80% 60% at 70% 20%, hsl(var(--space-nebula) / 0.15) 0%, transparent 50%),
            radial-gradient(ellipse 60% 40% at 20% 80%, hsl(var(--space-nebula) / 0.08) 0%, transparent 50%),
            hsl(var(--space-deep))
          `,
        }}
      />

      {/* Stars */}
      {stars.map((star) => (
        <div
          key={star.id}
          className="absolute rounded-full bg-star-bright twinkle"
          style={{
            left: `${star.x}%`,
            top: `${star.y}%`,
            width: `${star.size}px`,
            height: `${star.size}px`,
            "--twinkle-duration": `${star.duration}s`,
            "--twinkle-delay": `${star.delay}s`,
          } as React.CSSProperties}
        />
      ))}

      {/* Stars clustered around the sun */}
      {sunStars.map((star) => (
        <div
          key={`sun-star-${star.id}`}
          className="absolute rounded-full bg-star-bright twinkle"
          style={{
            left: `${star.x}%`,
            top: `${star.y}%`,
            width: `${star.size}px`,
            height: `${star.size}px`,
            "--twinkle-duration": `${star.duration}s`,
            "--twinkle-delay": `${star.delay}s`,
          } as React.CSSProperties}
        />
      ))}

      {/* Sun */}
      <div className="absolute" style={{ top: "-8%", left: "50%", transform: "translateX(-50%)" }}>
        {/* Corona rays */}
        <div
          className="absolute corona-rotate"
          style={{
            width: "500px",
            height: "500px",
            top: "50%",
            left: "50%",
            background: `conic-gradient(
              from 0deg,
              transparent 0deg, hsl(var(--sun-glow) / 0.14) 10deg, transparent 20deg,
              transparent 30deg, hsl(var(--sun-glow) / 0.09) 40deg, transparent 50deg,
              transparent 60deg, hsl(var(--sun-glow) / 0.14) 70deg, transparent 80deg,
              transparent 90deg, hsl(var(--sun-glow) / 0.09) 100deg, transparent 110deg,
              transparent 120deg, hsl(var(--sun-glow) / 0.14) 130deg, transparent 140deg,
              transparent 150deg, hsl(var(--sun-glow) / 0.09) 160deg, transparent 170deg,
              transparent 180deg, hsl(var(--sun-glow) / 0.14) 190deg, transparent 200deg,
              transparent 210deg, hsl(var(--sun-glow) / 0.09) 220deg, transparent 230deg,
              transparent 240deg, hsl(var(--sun-glow) / 0.14) 250deg, transparent 260deg,
              transparent 270deg, hsl(var(--sun-glow) / 0.09) 280deg, transparent 290deg,
              transparent 300deg, hsl(var(--sun-glow) / 0.14) 310deg, transparent 320deg,
              transparent 330deg, hsl(var(--sun-glow) / 0.09) 340deg, transparent 360deg
            )`,
            borderRadius: "50%",
            filter: "blur(8px)",
          }}
        />

        {/* Outer glow */}
        <div
          className="rounded-full"
          style={{
            width: "300px",
            height: "300px",
            background: `radial-gradient(circle, hsl(var(--sun-glow) / 0.28) 0%, hsl(var(--sun-corona) / 0.12) 50%, transparent 75%)`,
            position: "relative",
          }}
        >
          {/* Sun core */}
          <div
            className="absolute sun-pulse rounded-full"
            style={{
              width: "120px",
              height: "120px",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              background: `radial-gradient(circle, hsl(var(--sun-core)) 0%, hsl(var(--sun-glow)) 40%, hsl(var(--sun-corona)) 80%, transparent 100%)`,
            }}
          />
        </div>
      </div>

      {/* Horizon glow */}
      <div
        className="absolute bottom-0 left-0 right-0"
        style={{
          height: "2px",
          background: `linear-gradient(90deg, transparent 10%, hsl(var(--sun-glow) / 0.15) 50%, transparent 90%)`,
        }}
      />
    </div>
  );
};

export default SpaceScene;
