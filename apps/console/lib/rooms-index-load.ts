import type { Room } from "./api";

export type RoomsTryGetResult = { data: Room[] | null; authRequired: boolean };

/** Apply tryGet rooms result — auth flag stays sticky across polls. */
export function applyRoomsTryGet(
  prevAuth: boolean,
  roomsRes: RoomsTryGetResult
): { rooms: Room[]; adminAuthRequired: boolean } {
  return {
    rooms: roomsRes.data ?? [],
    adminAuthRequired: prevAuth || roomsRes.authRequired,
  };
}
