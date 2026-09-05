import React from "react";
import { Composition } from "remotion";
import { LoopDemo } from "./LoopDemo";
import { FilmEnd, FilmTitle } from "./FilmCards";
import { MacOsDemo, FPS, MACOS_DEMO_DURATION } from "./MacOsDemo";

const TITLE_FRAMES = 90;
const END_FRAMES = 90;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="LoopDemo"
        component={LoopDemo}
        durationInFrames={360}
        fps={FPS}
        width={1280}
        height={720}
      />
      <Composition
        id="MacOsDemo"
        component={MacOsDemo}
        durationInFrames={MACOS_DEMO_DURATION}
        fps={FPS}
        width={1280}
        height={720}
      />
      <Composition
        id="FilmTitle"
        component={FilmTitle}
        durationInFrames={TITLE_FRAMES}
        fps={FPS}
        width={1920}
        height={1080}
      />
      <Composition
        id="FilmEnd"
        component={FilmEnd}
        durationInFrames={END_FRAMES}
        fps={FPS}
        width={1920}
        height={1080}
      />
    </>
  );
};
