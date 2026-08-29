import React from "react";
import { Composition } from "remotion";
import { LoopDemo } from "./LoopDemo";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="LoopDemo"
      component={LoopDemo}
      durationInFrames={360}
      fps={30}
      width={1280}
      height={720}
    />
  );
};
