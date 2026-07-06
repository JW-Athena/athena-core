import { useState } from "react";

import type { AthenaPresenceState } from "./athenaPresenceState";

type AthenaFaceAssetProps = {
  state: AthenaPresenceState;
};

const ATHENA_FACE_ASSET_PATH = "/assets/athena/athena-face-canon.png";

export function AthenaFaceAsset({ state }: AthenaFaceAssetProps) {
  const [assetMissing, setAssetMissing] = useState(false);

  return (
    <div className={`athena-face-asset athena-face--${state}`}>
      {!assetMissing && (
        <img
          src={ATHENA_FACE_ASSET_PATH}
          alt="ATHENA"
          draggable={false}
          onError={() => setAssetMissing(true)}
        />
      )}

      {assetMissing && (
        <div className="athena-face-missing" role="status">
          ATHENA FACE ASSET MISSING
        </div>
      )}
    </div>
  );
}
