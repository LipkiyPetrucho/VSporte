from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from account.models import Friendship, Profile
from notifications.models import Notification

from .models import Community, CommunityInvitation, CommunityJoinRequest

User = get_user_model()


class CommunityMembershipBaseTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="group_owner",
            password="testpass123",
        )
        Profile.objects.get_or_create(user=self.owner)

        self.applicant = User.objects.create_user(
            username="group_applicant",
            password="testpass123",
        )
        Profile.objects.get_or_create(user=self.applicant)

        self.friend = User.objects.create_user(
            username="group_friend",
            password="testpass123",
        )
        Profile.objects.get_or_create(user=self.friend)

        self.outsider = User.objects.create_user(
            username="group_outsider",
            password="testpass123",
        )
        Profile.objects.get_or_create(user=self.outsider)

        Friendship.objects.create(
            from_user=self.owner,
            to_user=self.friend,
            status=Friendship.ACCEPTED,
        )

        self.community = Community.objects.create(
            owner=self.owner,
            name="Футбольный клуб",
            sport="football",
            description="Тестовая группа",
        )
        self.community.members.add(self.owner)

        self.join_url = reverse("groups:join")
        self.leave_url = reverse("groups:leave")
        self.membership_url = reverse("groups:membership")
        self.invite_url = reverse("groups:invite")

    def _post_join(self, user, community_id=None):
        self.client.force_login(user)
        return self.client.post(
            self.join_url,
            {"id": community_id or self.community.pk},
        )

    def _post_leave(self, user, community_id=None):
        self.client.force_login(user)
        return self.client.post(
            self.leave_url,
            {"id": community_id or self.community.pk},
        )

    def _post_membership(self, user, **data):
        self.client.force_login(user)
        return self.client.post(self.membership_url, data)

    def _post_invite(self, user, **data):
        self.client.force_login(user)
        return self.client.post(self.invite_url, data)


class CommunityCreateTest(CommunityMembershipBaseTest):
    def test_create_adds_owner_as_member(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("groups:create"),
            {
                "name": "Tennis Club",
                "sport": "tennis",
                "description": "Описание",
            },
        )
        community = Community.objects.get(name="Tennis Club")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, community.get_absolute_url())
        self.assertEqual(community.owner, self.owner)
        self.assertTrue(community.members.filter(pk=self.owner.pk).exists())


class CommunityJoinRequestTest(CommunityMembershipBaseTest):
    def test_join_creates_pending_request_and_notifies_owner(self):
        response = self._post_join(self.applicant)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["membership_status"], "pending")
        self.assertIn("join_request_id", data)

        join_request = CommunityJoinRequest.objects.get(
            community=self.community,
            user=self.applicant,
        )
        self.assertEqual(join_request.status, CommunityJoinRequest.PENDING)
        self.assertFalse(
            self.community.members.filter(pk=self.applicant.pk).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.owner,
                actor=self.applicant,
                notification_type=Notification.TYPE_GROUP_JOIN_REQUEST,
            ).exists()
        )

    def test_duplicate_pending_join_is_rejected(self):
        self._post_join(self.applicant)
        response = self._post_join(self.applicant)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(
            CommunityJoinRequest.objects.filter(
                community=self.community,
                user=self.applicant,
            ).count(),
            1,
        )

    def test_applicant_can_cancel_pending_request(self):
        join_response = self._post_join(self.applicant)
        request_id = join_response.json()["join_request_id"]

        response = self._post_membership(
            self.applicant,
            id=request_id,
            action="cancel",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

        join_request = CommunityJoinRequest.objects.get(pk=request_id)
        self.assertEqual(join_request.status, CommunityJoinRequest.CANCELLED)

    def test_owner_can_accept_join_request(self):
        join_response = self._post_join(self.applicant)
        request_id = join_response.json()["join_request_id"]

        response = self._post_membership(
            self.owner,
            id=request_id,
            action="accept",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["membership_status"], "joined")

        join_request = CommunityJoinRequest.objects.get(pk=request_id)
        self.assertEqual(join_request.status, CommunityJoinRequest.ACCEPTED)
        self.assertTrue(
            self.community.members.filter(pk=self.applicant.pk).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.applicant,
                actor=self.owner,
                notification_type=Notification.TYPE_GROUP_JOIN_ACCEPTED,
            ).exists()
        )

    def test_owner_can_reject_join_request(self):
        join_response = self._post_join(self.applicant)
        request_id = join_response.json()["join_request_id"]

        response = self._post_membership(
            self.owner,
            id=request_id,
            action="reject",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

        join_request = CommunityJoinRequest.objects.get(pk=request_id)
        self.assertEqual(join_request.status, CommunityJoinRequest.REJECTED)
        self.assertFalse(
            self.community.members.filter(pk=self.applicant.pk).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.applicant,
                actor=self.owner,
                notification_type=Notification.TYPE_GROUP_JOIN_REJECTED,
            ).exists()
        )

    def test_non_owner_cannot_accept_join_request(self):
        join_response = self._post_join(self.applicant)
        request_id = join_response.json()["join_request_id"]

        response = self._post_membership(
            self.outsider,
            id=request_id,
            action="accept",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "error")

        join_request = CommunityJoinRequest.objects.get(pk=request_id)
        self.assertEqual(join_request.status, CommunityJoinRequest.PENDING)
        self.assertFalse(
            self.community.members.filter(pk=self.applicant.pk).exists()
        )

    def test_rejected_user_can_reapply(self):
        join_response = self._post_join(self.applicant)
        request_id = join_response.json()["join_request_id"]
        self._post_membership(self.owner, id=request_id, action="reject")

        response = self._post_join(self.applicant)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["membership_status"], "pending")

        join_request = CommunityJoinRequest.objects.get(pk=request_id)
        self.assertEqual(join_request.status, CommunityJoinRequest.PENDING)


class CommunityInvitationTest(CommunityMembershipBaseTest):
    def test_owner_can_invite_friend(self):
        response = self._post_invite(
            self.owner,
            action="invite",
            community_id=self.community.pk,
            to_user_id=self.friend.pk,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("invitation_id", data)

        invitation = CommunityInvitation.objects.get(pk=data["invitation_id"])
        self.assertEqual(invitation.status, CommunityInvitation.PENDING)
        self.assertEqual(invitation.from_user, self.owner)
        self.assertEqual(invitation.to_user, self.friend)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.friend,
                actor=self.owner,
                notification_type=Notification.TYPE_GROUP_INVITATION,
            ).exists()
        )

    def test_cannot_invite_non_friend(self):
        response = self._post_invite(
            self.owner,
            action="invite",
            community_id=self.community.pk,
            to_user_id=self.outsider.pk,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertFalse(
            CommunityInvitation.objects.filter(
                community=self.community,
                to_user=self.outsider,
            ).exists()
        )

    def test_non_owner_cannot_invite(self):
        response = self._post_invite(
            self.applicant,
            action="invite",
            community_id=self.community.pk,
            to_user_id=self.friend.pk,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "error")
        self.assertFalse(
            CommunityInvitation.objects.filter(
                community=self.community,
                to_user=self.friend,
            ).exists()
        )

    def test_invitee_can_accept_invitation(self):
        invite_response = self._post_invite(
            self.owner,
            action="invite",
            community_id=self.community.pk,
            to_user_id=self.friend.pk,
        )
        invitation_id = invite_response.json()["invitation_id"]

        response = self._post_invite(
            self.friend,
            action="accept",
            id=invitation_id,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["membership_status"], "joined")

        invitation = CommunityInvitation.objects.get(pk=invitation_id)
        self.assertEqual(invitation.status, CommunityInvitation.ACCEPTED)
        self.assertTrue(
            self.community.members.filter(pk=self.friend.pk).exists()
        )

    def test_invitee_can_decline_invitation(self):
        invite_response = self._post_invite(
            self.owner,
            action="invite",
            community_id=self.community.pk,
            to_user_id=self.friend.pk,
        )
        invitation_id = invite_response.json()["invitation_id"]

        response = self._post_invite(
            self.friend,
            action="decline",
            id=invitation_id,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["membership_status"], "none")

        invitation = CommunityInvitation.objects.get(pk=invitation_id)
        self.assertEqual(invitation.status, CommunityInvitation.DECLINED)
        self.assertFalse(
            self.community.members.filter(pk=self.friend.pk).exists()
        )

    def test_owner_can_cancel_invitation(self):
        invite_response = self._post_invite(
            self.owner,
            action="invite",
            community_id=self.community.pk,
            to_user_id=self.friend.pk,
        )
        invitation_id = invite_response.json()["invitation_id"]

        response = self._post_invite(
            self.owner,
            action="cancel",
            id=invitation_id,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

        invitation = CommunityInvitation.objects.get(pk=invitation_id)
        self.assertEqual(invitation.status, CommunityInvitation.CANCELLED)

    def test_accepting_invitation_cancels_pending_join_request(self):
        join_response = self._post_join(self.friend)
        join_request_id = join_response.json()["join_request_id"]

        invite_response = self._post_invite(
            self.owner,
            action="invite",
            community_id=self.community.pk,
            to_user_id=self.friend.pk,
        )
        invitation_id = invite_response.json()["invitation_id"]

        response = self._post_invite(
            self.friend,
            action="accept",
            id=invitation_id,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

        join_request = CommunityJoinRequest.objects.get(pk=join_request_id)
        self.assertEqual(join_request.status, CommunityJoinRequest.CANCELLED)
        self.assertTrue(
            self.community.members.filter(pk=self.friend.pk).exists()
        )


class CommunityModerationTest(CommunityMembershipBaseTest):
    def test_owner_can_remove_member(self):
        self.community.members.add(self.applicant)
        CommunityJoinRequest.objects.create(
            community=self.community,
            user=self.applicant,
            status=CommunityJoinRequest.ACCEPTED,
        )

        response = self._post_membership(
            self.owner,
            action="remove_member",
            community_id=self.community.pk,
            user_id=self.applicant.pk,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertFalse(
            self.community.members.filter(pk=self.applicant.pk).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.applicant,
                actor=self.owner,
                notification_type=Notification.TYPE_GROUP_MEMBER_REMOVED,
            ).exists()
        )
        join_request = CommunityJoinRequest.objects.get(
            community=self.community,
            user=self.applicant,
        )
        self.assertEqual(join_request.status, CommunityJoinRequest.CANCELLED)

    def test_cannot_remove_owner(self):
        response = self._post_membership(
            self.owner,
            action="remove_member",
            community_id=self.community.pk,
            user_id=self.owner.pk,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "error")
        self.assertTrue(
            self.community.members.filter(pk=self.owner.pk).exists()
        )

    def test_non_owner_cannot_remove_member(self):
        self.community.members.add(self.applicant)
        response = self._post_membership(
            self.outsider,
            action="remove_member",
            community_id=self.community.pk,
            user_id=self.applicant.pk,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "error")
        self.assertTrue(
            self.community.members.filter(pk=self.applicant.pk).exists()
        )

    def test_member_can_leave(self):
        self.community.members.add(self.applicant)
        CommunityJoinRequest.objects.create(
            community=self.community,
            user=self.applicant,
            status=CommunityJoinRequest.ACCEPTED,
        )

        response = self._post_leave(self.applicant)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["membership_status"], "none")
        self.assertFalse(
            self.community.members.filter(pk=self.applicant.pk).exists()
        )
        join_request = CommunityJoinRequest.objects.get(
            community=self.community,
            user=self.applicant,
        )
        self.assertEqual(join_request.status, CommunityJoinRequest.CANCELLED)

    def test_owner_cannot_leave(self):
        response = self._post_leave(self.owner)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertTrue(
            self.community.members.filter(pk=self.owner.pk).exists()
        )

    def test_leave_response_does_not_count_members(self):
        self.community.members.add(self.applicant)
        with CaptureQueriesContext(connection) as ctx:
            response = self._post_leave(self.applicant)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["members_count"], 1)
        count_queries = [
            query["sql"]
            for query in ctx.captured_queries
            if "groups_community_members" in query["sql"]
            and "COUNT(*)" in query["sql"].upper()
        ]
        self.assertEqual(count_queries, [])


class CommunityListQueryTests(CommunityMembershipBaseTest):
    def test_list_annotates_members_count_without_per_row_count(self):
        self.community.slug = "football-club"
        self.community.save(update_fields=["slug"])
        second = Community.objects.create(
            owner=self.owner,
            name="Tennis Club",
            sport="tennis",
            slug="tennis-club",
        )
        second.members.add(self.owner, self.friend)

        self.client.force_login(self.owner)
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(reverse("groups:list"))
        self.assertEqual(response.status_code, 200)
        communities = list(response.context["communities"])
        counts = {community.slug: community.members_count for community in communities}
        self.assertEqual(counts["football-club"], 1)
        self.assertEqual(counts["tennis-club"], 2)

        extra_counts = [
            query["sql"]
            for query in ctx.captured_queries
            if 'FROM "groups_community_members"' in query["sql"]
            and "COUNT(*)" in query["sql"].upper()
        ]
        self.assertEqual(extra_counts, [])
